from operator import truediv
import os, json, pytz
import pandas as pd
from re import U
from flask import Flask
import tweepy, config, sheets
from datetime import datetime, timedelta

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
            app.logger.debug('Deleted {0}'.format(results))
        else:
            if not user_id:
                user_id = self.user_id
            results = self.db.users.find_one_and_update(
                filter={'user_id': user_id},
                update={'$unset': {'followers': ''}}
            )
            app.logger.debug('Deleted {0}'.format(results))

    def dedup_followers(self, user_id=None):
        users = None
        if user_id:
            users = [self.db.users.find_one(filter={'user_id': user_id})]
        else:
            users = self.db.users.find()
        for user in users:
            pass

    def _check_follower_exists(self, user_id, follower: tweepy.models.User):
        try:
            exists = self.db.users.find_one(
                filter={
                    'user_id': user_id,
                    'followers.id': follower.id
                }
            )
            if exists:
                app.logger.debug('Follower {0} exists.'.format(follower['screen_name']))
                return True
            else:
                return False
            # for old_follower in self.get_old_followers(user_id):
            #     if old_follower['id'] == follower.id:
            #         return True
            #     else:
            #         return False
        except Exception as e:
            raise e
            app.logger.error(e)
            return True

    def get_new_followers(self, user_id=None, handle=None) -> None:
        if not user_id:
            user_id = self.user_id
        elif handle:
            user_id = self.db.users.find_one(filter={'screen_name': handle})
        followers = []
        for page in tweepy.Cursor(self.api.get_followers, user_id=user_id).pages():
            for follower in page:
                exists = self._check_follower_exists(user_id, follower)
                follower_json = follower._json
                follower_json['messaged'] = False
                if exists:
                    app.logger.debug('Follower {0} exists.'.format(follower.screen_name))
                    # self.db.users.update_one(
                    #     filter={'user_id': user_id},
                    #     update={
                    #         '$set': {'followers.$[element]': follower_json}
                    #     },
                    #     array_filters={[ 
                    #         { "element.id": { '$eq': follower['id'] } } 
                    #     ]},
                    #     upsert=False
                    # )
                else:
                    self.db.users.update_one(
                        filter={'user_id': user_id},
                        update={
                            '$addToSet': {'followers': follower_json}
                        },
                        upsert=False
                    )
            # followers.extend(page)
            # app.logger.info(followers)
        app.logger.info('Got {0} followers.'.format(len(followers)))

    def seed_db(self, user_id):
        old = self.get_old_followers(user_id)
        if not old:
            new = self.get_new_followers(user_id)

    def get_old_followers(self, user_id):
        user = self.db.users.find_one(filter={'user_id': user_id})
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
        self.sheets.update()
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
        app.logger.debug('Client row: {0}'.format(client_row))
        for label_col, url_col in zip(cta_labels, cta_urls):
            alpha = client_row[label_col].str.match('[a-z0-9]*', case=False)
            has_empty_label = client_row[label_col].str.isspace()
            has_empty_url = client_row[url_col].str.isspace()
            if alpha.all() and not has_empty_label.any() and not has_empty_url.any():
                if len(client_row[label_col]) > 36:
                    app.logger.error("{0} too long!".format(label_col))
                else:
                    ctas.append({
                        "type": "web_url",
                        "label": client_row[label_col].iat[0],
                        "url": client_row[url_col].iat[0]
                    })
                app.logger.debug('CTAs: {0}'.format(ctas))
        return ctas

    def direct_message(self, from_userid=None, to_userid=None):
        if not from_userid:
            from_userid = self.user_id
        # first_name = self.get_username(to_userid).split(' ')[0]
        self.generate_dm_text(to_userid)
        user = self.db.users.find_one({'user_id': self.user_id})
        dm_text = user['script']
        ctas = self.construct_ctas(user['screen_name'])
        self.api.send_direct_message(to_userid, text=dm_text, ctas=ctas)
        result = self.db.users.update_many(
            filter={
                'user_id': user['user_id'],
                'followers.id': {'$eq': to_userid}
            },
            update={'$set': {'followers.$.messaged': True}},
            # array_filters=[{ 'element.id': { '$eq': to_userid } }],
            # upsert=True
        )
        app.logger.debug(result.raw_result)
        app.logger.debug('Sent message from {0} to {1}'.format(
            user['screen_name'],
            to_userid
        ))

    def filter_inactive(self, client, follower):
        filter_df = self.sheets.get_df()
        client_filter = filter_df[filter_df['Handle'] == client]['Minimum Account Age'][0]
        creation_date_utc = pd.to_datetime(
            follower['created_at'], 
            # "Mon Nov 29 21:18:15 +0000 2010"
            format='%a %b %d %H:%M:%S %z %Y',
            utc=True
        )
        account_age = datetime.now(pytz.timezone('America/New_York')) - creation_date_utc
        if account_age / timedelta(weeks=1) > float(client_filter):
            return True
        return False

    def filter_status_count(self, client, follower):
        filter_df = self.sheets.get_df()
        client_filter = filter_df[filter_df['Handle'] == client]['Minimum Posts'][0]
        if follower['statuses_count'] > int(client_filter):
            return True
        return False

    def filter_follower_count(self, client, follower):
        filter_df = self.sheets.get_df()
        client_filter = filter_df[filter_df['Handle'] == client]['Minimum Followers'][0]
        if follower['followers_count'] > int(client_filter):
            return True
        return False

    def filter_blocked(self, client, follower):
        blocklist = self.sheets.get_blocklist(client)
        blocked = False
        try:
            blocked = blocklist.str.contains(follower['screen_name']).any()
        except Exception as e:
            app.logger.error(e)
            return False
        return blocked

    def direct_message_all_followers(self):
        user_id = self.user_id
        user = self.db.users.find_one({'user_id': self.user_id})
        self.sheets.update()
        client = user['screen_name']
        for follower in self.get_old_followers(user_id):
            self.sheets.update()
            blocked = self.filter_blocked(client, follower)
            active = self.filter_inactive(client, follower)
            enough_posts = self.filter_status_count(client, follower)
            enough_followers = self.filter_follower_count(client, follower)
            messaged = follower['messaged']
            if not messaged and not blocked and active and enough_posts and enough_followers:
                app.logger.debug('Follower {0} passed filters: {1} {2} {3} {4}'.format(
                    follower['screen_name'], blocked, active, enough_posts, enough_followers
                ))
                self.direct_message(self.user_id, follower['id'])
            else:
                app.logger.info(
                    'Follower {0} has been messaged, blocked or filtered out.'.format(follower['screen_name'])
                )
