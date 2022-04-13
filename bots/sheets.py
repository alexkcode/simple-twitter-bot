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
        self._scripts_id = None
        self._blocklist_id = None
        if cred_location == None:
            self.cred_location = app.config['CRED_LOCATION']
        else:
            self.cred_location = cred_location
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
                self.create_scripts_tab()
                self.create_blocklist()
                if isinstance(self.sh, gspread.spreadsheet.Spreadsheet):
                    app.logger.info("Successfully acquired spreadsheet instance.")
        except Exception as e:
            raise e

    def create_token(self):
        if os.path.exists(self.cred_location) and not self.creds:
            self.creds = Credentials.from_service_account_file(self.cred_location, scopes=self.scopes)

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
        sheet = {}
        sheet["id"] = sh.id
        sheet["title"] = sh.title
        sheet["url"] = sh.url
        sh.share(app.config['EMAIL1'], perm_type='user', role='writer')
        sh.share(app.config['EMAIL2'], perm_type='user', role='writer')
        self.db.sheets.insert_one(sheet)
        app.logger.warning("Old sheet was not found. Created new sheet {0}.".format(sheet))

    def create_scripts_tab(self):
        try:
            ws = self.sh.worksheet('Scripts')
            ws.batch_update([{
                'range': 'A1:M1',
                'values': [[
                    'ID','Handle', 'Script', 'Job', 
                    'CTA 1 Label', 'CTA 1 Url', 
                    'CTA 2 Label', 'CTA 2 Url', 
                    'CTA 3 Label', 'CTA 3 Url',
                    'Minimum Posts', 'Minimum Followers',
                    'Minimum Account Age (weeks)'
                ]],
            }])
        except Exception as e:
            ws = self.sh.add_worksheet('Scripts', 100, 20)
            raise e

    def update(self):
        self.create_token()
        gsp = Spread(
            self.sh_url, 
            sheet='Scripts', 
            config=None, 
            create_spread=False, 
            create_sheet=False, 
            scope=self.scopes,
            user='default', 
            creds=self.creds, 
            client=None, 
            permissions=None
        )
        self._df = gsp.sheet_to_df(index=None)
        app.logger.debug('Sheets df: {0}'.format(self._df))
        gsp = Spread(
            self.sh_url, 
            sheet='Blocklist', 
            config=None, 
            create_spread=False, 
            create_sheet=False, 
            scope=self.scopes,
            user='default', 
            creds=self.creds, 
            client=None, 
            permissions=None
        )
        self._blocklist = gsp.sheet_to_df(index=None)


    def upload(self, df):
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
        gsp.df_to_sheet(df, index=False, headers=True)
        app.logger.warning('Uploaded config sheet.')

    def get_script(self, handle):
        # ws = self.sh.get_worksheet(0)
        # self.update()
        return self._df[self._df['Handle'] == handle]['Script']

    def job_status(self, handle):
        # self.update()
        return self._df[self._df['Handle'] == handle]['Job']

    def set_userids(self):
        self.update()
        users = self.db.users.find()
        for user in users:
            handle = user['screen_name']
            self._df[self._df['Handle'] == handle]['ID'] = user['id']
        self.upload(self._df)

    def create_blocklist(self):
        try:
            self.sh.worksheet("Blocklist")
        except Exception as e:
            self.sh.add_worksheet("Blocklist", 10, 10)
            if 'already exists' in str(e):
                app.logger.warning(e)
            else:
                raise e

    def get_blocklist(self, handle):
        # self.update()
        return self._blocklist[handle]

    def get_df(self):
        # self.update()
        return self._df