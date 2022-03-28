import gspread
from gspread_pandas import Spread, Client
import pandas as pd
import os
from flask import Flask, request, g, session

from google.auth.transport.requests import Request
# from google.oauth2.credentials import Credentials
from google.oauth2.service_account import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
# from googleapiclient.errors import HttpError

app = Flask(__name__)
app.config.from_object('config.Config')

class SheetsWrapper(object):

    def __init__(self, db, gc:gspread.Client, cred_location=None) -> None:
        self.db = db
        self.gc = gc
        self.sh = None
        self.creds = None
        if cred_location == None:
            self.cred_location = app.config['CRED_LOCATION']
        else:
            self.cred_location = cred_location
        # self.token_location = 'token.json'
        self.scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        # create spreadsheet for twitter bot configuration
        try:
            found_sheet = self.db.sheets.find_one({"title": "Twitter Bot Configuration"})
            if not found_sheet:
                app.logger.warning("Old config sheet was not found. Creating new one...")
                self.create_config_sheet()
            else:
                self.sh_url = found_sheet['url']
                app.logger.info('Reading from Google Sheet {0}'.format(self.sh_url))
                self.sh = self.gc.open_by_url(self.sh_url)
                ws = self.sh.get_worksheet(0)
                ws.update_title("Scripts")
                ws.batch_update([{
                    'range': 'A1:C1',
                    'values': [['Handle', 'Script', '']],
                }])
                if isinstance(self.sh, gspread.spreadsheet.Spreadsheet):
                    app.logger.info("Successfully acquired spreadsheet instance.")
        except Exception as e:
            # self.create_config_sheet()
            raise e

    def create_token(self):
        if os.path.exists(self.cred_location):
            self.creds = Credentials.from_service_account_file(self.cred_location, scopes=self.scopes)
        # If there are no (valid) credentials available, let the user log in.
        # if not self.creds or not self.creds.valid:
        #     print('No token found')
        #     if creds and creds.expired and creds.refresh_token:
        #         creds.refresh(Request())
        #     else:
        #         flow = InstalledAppFlow.from_client_secrets_file(
        #             self.cred_location, self.scopes)
        #         creds = flow.run_local_server(port=8000)
        #     # Save the credentials for the next run
        #     with open(self.token_location, 'w') as token:
        #         token.write(creds.to_json())

    def get_gspread(self):
        with app.app_context():
            if not 'gc' in g:
                self.gc = gspread.service_account(filename=self.cred_location)
                g.gc=self.gc
                return g.gc
            else:
                return self.gc

    def create_config_sheet(self):
        # if self.db.sheets.find_one({"title": "Twitter Bot Configuration"}):
        #     app.logger.info("Config sheet exists already at {0}.".format(
        #         str(self.db.sheets.find_one({"title": "Twitter Bot Configuration"}))[0]['url']
        #     ))
        # else:
        sh = self.gc.create("Twitter Bot Configuration")
        app.logger.info("Created new spreadsheet instance.")
        self.sh = sh
        sheet = {}
        sheet["id"] = sh.id
        sheet["title"] = sh.title
        sheet["url"] = sh.url
        sh.share(app.config['EMAIL1'], perm_type='user', role='writer')
        self.db.sheets.insert_one(sheet)
        app.logger.warning("Old sheet was not found. Created new sheet {0}.".format(sheet))

    def update(self):
        self.create_token()
        gsp = Spread(
            self.sh_url, 
            sheet=0, 
            config=None, 
            create_spread=False, 
            create_sheet=False, 
            scope=self.scopes,
            user='default', 
            creds=self.creds, 
            client=None, 
            permissions=None
        )
        self._df = gsp.sheet_to_df()
        app.logger.info(self._df)

    def set_script(self):
        pass

    def get_script(self, handle):
        ws = self.sh.get_worksheet(0)
        pass