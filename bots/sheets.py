import gspread
import pandas as pd
import os

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.errors import HttpError

app = Flask(__name__)

# location of google oauth credentials
CRED_LOCATION = ''
TOKEN_LOCATION = 'token.json'
SCOPES = app.config['SCOPES']

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
            creds = flow.run_local_server(port=5000)
        # Save the credentials for the next run
        with open(TOKEN_LOCATION, 'w') as token:
            token.write(creds.to_json())

def read_config():
    gc = gspread.oauth(
        credentials_filename=CRED_LOCATION,
        authorized_user_filename=TOKEN_LOCATION
    )

    sht1 = gc.open('Frakture SMS Raw Import')
    pass

