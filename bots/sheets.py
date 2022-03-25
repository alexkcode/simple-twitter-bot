import gspread, redis, gspread_pandas
import pandas as pd
import os
from flask import Flask, request, g, session

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
# from googleapiclient.errors import HttpError

app = Flask(__name__)
app.config.from_object('config.Config')

class SheetsWrapper(object):

    def __init__(self, db:redis.Redis, gc:gspread.Client, cred_location=None) -> None:
        self.db = db
        self.gc = gc
        self.sh = None
        if cred_location == None:
            self.cred_location = app.config['CRED_LOCATION']
        else:
            self.cred_location = cred_location
        self.token_location = 'token.json'
        self.scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        try:
            # need to stringify otherwise it will return bytes format
            self.sh_url = str(db.hget("sheet", "url"))
            if self.sh_url is None:
                self.create_config_sheet()
            else:
                app.logger.info('Reading from Google Sheet {0}'.format(self.sh_url))
                self.sh = self.gc.open_by_url(self.sh_url)
                if isinstance(self.sh, gspread.spreadsheet.Spreadsheet):
                    app.logger.info("Successfully acquired spreadsheet instance.")
        except Exception as e:
            self.create_config_sheet()
            raise e

    def create_token(self):
        creds = None
        if os.path.exists(self.token_location):
            creds = Credentials.from_authorized_user_file(self.token_location, self.scopes)
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            print('No token found')
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.cred_location, self.scopes)
                creds = flow.run_local_server(port=8000)
            # Save the credentials for the next run
            with open(self.token_location, 'w') as token:
                token.write(creds.to_json())

    def get_gspread(self):
        with app.app_context():
            if not 'gc' in g:
                self.gc = gspread.service_account(filename=self.cred_location)
                g.gc=self.gc
                return g.gc
            else:
                return self.gc

    def create_config_sheet(self):
        sh = self.gc.create("Twitter Bot Configuration")
        app.logger.info("Created new spreadsheet instance.")
        self.sh = sh
        self.db.hset("sheet", "id", sh.id)
        self.db.hset("sheet", "title", sh.title)
        self.db.hset("sheet", "url", sh.url)
        sh.share(app.config['EMAIL1'], perm_type='user', role='writer')
        app.logger.warning("Old sheet was not found. Created new sheet {0} {1} {2}.".format(
            str(self.db.hget("sheet", "title")),
            str(self.db.hget("sheet", "id")),
            str(self.db.hget("sheet", "url"))
        ))
        ws = self.sh.get_worksheet(0)
        ws.update_title("Scripts")
        ws.batch_update([{
            'range': 'A1:C1',
            'values': [['Handle', 'Script', '']],
        }])

    def update(self):
        self._gcp = gspread_pandas.spread.Spread(
            self.sh_url, 
            sheet=0, 
            config=None, 
            create_spread=False, 
            create_sheet=False, 
            scope=self.scopes
            user='default', 
            creds=None, 
            client=None, 
            permissions=None
        )
        pass

    def set_script(self):
        pass

    def get_script(self, handle):
        ws = self.sh.get_worksheet(0)