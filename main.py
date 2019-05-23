#!/usr/bin/env python3
from __future__ import print_function
import pickle
import os.path
import sys
import re
import time
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/drive.file']

BLOG_FOLDER="imghosting"

def get_service():
    creds = None
    home = os.path.expanduser('~')
    if os.path.exists(home+'/.cred/token.pickle'):
        with open(home+'/.cred/token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                home+'/.cred/credentials.json', SCOPES)
            creds = flow.run_local_server()
        # Save the credentials for the next run
        with open(home+'/.cred/token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    return build('drive', 'v3', credentials=creds)

def create_folder(service, name, parents):
    fname = {
        'name': name,
        'mimeType': 'application/vnd.google-apps.folder',
        'parents':[parents]
    }
    folder = service.files().create(body=fname,
                                            fields='id').execute()
    return folder['id']

def check_create_folder(service):
    id=None
    # Call the Drive v3 API
    results = service.files().list(
        pageSize=10, fields="nextPageToken, files(id, name)").execute()
    items = results.get('files', [])
    result = list(filter(lambda item: item['name'] == BLOG_FOLDER, items))
    print(result)

    if len(result) == 0:
        fname = {
            'name': BLOG_FOLDER,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        folder = service.files().create(body=fname,
                                            fields='id').execute()
        print ('Folder ID: %s' % folder.get('id'))
        id = folder.get('id')
    else:
        folder = result[0]
        print ('Already Exist Folder ID: %s' % folder.get('id'))
        id = folder.get('id')
    return id


def upload_img(service, folder_id, img):
    fmeta = {'name':img, 'parents':[folder_id]}
    media = MediaFileUpload(
            './'+img,
            mimetype='image/jpeg',
            resumable=True
            )
    upload = service.files().create(
            body=fmeta,
            media_body=media,
            fields='id'
            ).execute()
    uploadid = upload['id']
    permission = {'type': 'anyone','role':'reader'}

    result = service.permissions().create(
            fileId=uploadid,
            body=permission,
            fields='id'
            ).execute()
    return 'http://drive.google.com/uc?export=view&id='+uploadid


def main(fname):
    service = get_service()
    hosting_id = check_create_folder(service)
    folder_id = create_folder(service, fname, hosting_id)

    src_file = open(fname, 'r')
    dest_file = open(fname+'.compiled', 'w')
    img_pat = re.compile(r'\!\[.*\]\((?!http)(.*)\)')
    while True:
        line = src_file.readline()
        if not line: break
        img_list = img_pat.findall(line)
        for img in img_list:
            host_url = upload_img(service, folder_id, img)
            line = line.replace(img, host_url)
        dest_file.write(line)

    src_file.close()
    dest_file.close()


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("uses : program markdown_src")
        sys.exit(-1)
    fname = sys.argv[1]
    main(fname)
