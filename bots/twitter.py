import os, json, pytz
import pandas as pd
from re import U
from flask import Flask
import tweepy, config, sheets
from datetime import datetime

app = Flask(__name__)

class TwitterWrapper(object):

    def __init__(self, db, api:tweepy.API, sheets:sheets.SheetsWrapper, user_id=None) -> None:
        self.db = db
        self.api = api
        self.user_id = user_id
        self.sheets = sheets

    def delete_followers(self, user_id=None, screen_name=None):
        if screen_name:
            results = self.db.users.find_one_and_update(
                filter={'screen_name': screen_name},
                update={'$unset': {'followers': ''}}
            )
            app.logger.info('Deleted {0}'.format(results))
        else:
            if not user_id:
                user_id = self.user_id
            results = self.db.users.find_one_and_update(
                filter={'user_id': user_id},
                update={'$unset': {'followers': ''}}
            )
            app.logger.info('Deleted {0}'.format(results))

    def dedup_followers(self, user_id=None):
        users = None
        if user_id:
            users = [self.db.users.find_one(filter={'user_id': user_id})]
        else:
            users = self.db.users.find()
        for user in users:
            pass

    def _check_follower_exists(self, user_id, follower):
        exists = None
        try:
            exists = self.db.users.find_one(
                filter={
                    'user_id': {
                        '$eq': user_id,
                        '$elemMatch': {'id': follower['id']}
                    }
                }
                # array_filters={[ 
                #     { "followers.id": { '$eq': follower['id'] } } 
                # ]}
            )
        except Exception as e:
            app.logger.error(e)
        follower_json = follower._json
        follower_json['messaged'] = False
        if exists:
            self.db.users.update_one(
                filter={'user_id': user_id},
                update={
                    '$set': {'followers.$[element]': follower._json}
                },
                array_filters={[ 
                    { "element.id": { '$eq': follower['id'] } } 
                ]},
                upsert=False
            )
        else:
            self.db.users.update_one(
                filter={'user_id': user_id},
                update={
                    '$addToSet': {'followers': follower._json}
                },
                upsert=False
            )

    def get_new_followers(self, user_id=None, handle=None) -> None:
        if not user_id:
            user_id = self.user_id
        elif handle:
            user_id = self.db.users.find_one(filter={'screen_name': handle})
        followers = []
        for page in tweepy.Cursor(self.api.get_followers, user_id=user_id).pages():
            for follower in page:
                # app.logger.info(follower)
                # follower['user_id'] = follower['id_str'] + ':follower'
                # followers.append(follower._json)
                self._check_follower_exists(user_id, follower)
            # followers.extend(page)
            # app.logger.info(followers)
        # app.logger.info(self.db.users.find_one(filter={'user_id': user_id}))
        app.logger.info('Got {0} followers.'.format(len(followers)))

    def seed_db(self, user_id):
        old = self.get_old_followers(user_id)
        if not old:
            new = self.get_new_followers(user_id)
            self.save_followers(user_id, new)

    def get_old_followers(self, user_id):
        ids = []
        user = self.db.users.find_one(filter={'user_id': user_id})
        try:
            followers = user['followers']
            for follower in followers:
                ids.append(follower['id_str'])
                # app.logger.info(follower[0]['id_str'])
            # app.logger.info('Old followers: {0}'.format(ids))
        except Exception as e:
            raise e
        # return ids
        return user['followers']

    def generate_dm_text(self, user_id=None):
        """
        Generate DM text based on script from Google Drive
        """
        users = None 
        if user_id:
            users = self.db.users.find(filter={'user_id': user_id})
        else:
            users = self.db.users.find({'user_id': user_id})
        for user in users:
            script = self.sheets.get_script(user['screen_name'])
            # app.logger.info('Getting script for {0}: {1}'.format(user['screen_name'], script))
            if script[0]:
                self.db.users.find_one_and_update(
                    filter={'user_id': self.user_id},
                    update={'$set': {'script': script[0]}}
                )

    def construct_ctas(self, client_handle):
        config_df = self.sheets.get_df()
        client_row = config_df[config_df['Handle'] == client_handle]
        cta_labels = ['CTA 1 Label', 'CTA 2 Label', 'CTA 3 Label']
        cta_urls = ['CTA 1 Url', 'CTA 2 Url', 'CTA 3 Url']
        ctas = []
        for label_col, url_col in zip(cta_labels, cta_urls):
            match = client_row[label_col].str.match('[a-z0-9]*', case=False)
            if match.all():
                if len(client_row[label_col][0]) > 36:
                    app.logger.error("{0} too long!".format(label_col))
                else:
                    ctas.append({
                        "type": "web_url",
                        "label": client_row[label_col][0],
                        "url": client_row[url_col][0]
                    })
        return ctas

    def direct_message(self, from_userid=None, to_userid=None):
        if not from_userid:
            from_userid = self.user_id
        # first_name = self.get_username(to_userid).split(' ')[0]
        self.generate_dm_text(to_userid)
        user = self.db.users.find_one({'user_id': self.user_id})
        dm_text = user['script']
        ctas = self.construct_ctas(self.user_id)
        # self.api.send_direct_message(to_userid, text=dm_text, ctas=ctas)
        result = self.db.users.update_many(
            filter={
                'user_id': user['user_id'],
                'followers.id': {'$eq': to_userid}
            },
            update={'$set': {'followers.$.messaged': True}},
            # array_filters=[{ 'element.id': { '$eq': to_userid } }],
            # upsert=True
        )
        app.logger.info(result.raw_result)
        app.logger.info('Sent message from {0} to {1}'.format(
            user['screen_name'],
            to_userid
        ))

    def filter_inactive(self, follower):
        """
        Filter out new accounts, accounts with zero followers
        and accounts with fewer than 20 tweets
        """
        creation_date_utc = pd.to_datetime(
            follower['created_at'], 
            # "Mon Nov 29 21:18:15 +0000 2010"
            format='%a %b %d %H:%M:%S %z %Y',
            utc=True
        )
        account_age = datetime.now(pytz.timezone('America/New_York')) - creation_date_utc
        if follower['statuses_count'] > 20 and follower['followers_count'] > 0:
            if account_age.days > 365:
                return True
        return False

    def filter_follower(self, handle):
        filter_df = self.sheets.get_df()
        filter_df[filter_df['Handle'] == handle]
        pass

    def direct_message_all_followers(self):
        user_id = self.user_id
        user = self.db.users.find_one({'user_id': self.user_id})
        blocklist = self.sheets.get_blocklist(user['screen_name'])
        for follower in self.get_old_followers(user_id):
            if blocklist.str.contains(follower['screen_name']).any():
                app.logger.info('Follower {0} is blocked.'.format(follower['screen_name']))
            else:
                self.direct_message(self.user_id, follower['id'])
