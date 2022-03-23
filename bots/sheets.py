import gspread, redis
import pandas as pd
import os
from flask import Flask, request, g, session

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
# from googleapiclient.errors import HttpError

app = Flask(__name__)
app.config.from_object('config.Config')

# location of google oauth credentials
CRED_LOCATION = app.config['CRED_LOCATION']
TOKEN_LOCATION = 'token.json'
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

def create_token():
    creds = None
    if os.path.exists(TOKEN_LOCATION):
        creds = Credentials.from_authorized_user_file(TOKEN_LOCATION, SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        print('No token found')
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                CRED_LOCATION, SCOPES)
            creds = flow.run_local_server(port=8000)
        # Save the credentials for the next run
        with open(TOKEN_LOCATION, 'w') as token:
            token.write(creds.to_json())

def gspread_auth():
    with app.app_context():
        if not 'gc' in g:
            g.gc = gspread.service_account(filename=CRED_LOCATION)
        return g.gc

