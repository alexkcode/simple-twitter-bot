from operator import truediv
import os, json, pytz, time
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
                app.logger.debug('Follower {0} exists.'.format(follower.screen_name))
                return True
            else:
                return False
        except Exception as e:
            raise e

    def remove_unfollowed(self, user_id=None) -> None:
        if not user_id:
            user_id = self.user_id
        current_followers = []
        stored_account = self.db.users.find_one(filter={'user_id': user_id})
        if 'followers' in stored_account:
            stored_followers = stored_account['followers']
            for page in tweepy.Cursor(self.api.get_follower_ids, user_id=user_id, count=5000).pages():
                current_followers.extend(page)
            app.logger.warning("Current followers: {0}\nStored Followers: {1}".format(current_followers, stored_followers))
            for stored_follower in stored_followers:
                if stored_follower['id'] not in current_followers:
                    exists = self.db.users.find_one_and_update(
                        filter={
                            'user_id': user_id,
                            'followers.id': {'$eq': stored_follower['id']}
                        },
                        update={
                            '$pull': {
                                'followers': {
                                    'id': stored_follower['id']
                                }
                            }
                        } 
                    )
                    app.logger.warning('Follower {0} removed.'.format(stored_follower['screen_name']))

    def _disaggregate_followers(self, user_id=None) -> None:
        self.db.users.aggregate(
            pipeline =  ""
        )
        pass

    def get_new_followers(self, user_id=None) -> None:
        if not user_id:
            user_id = self.user_id
        followers = []
        for page in tweepy.Cursor(self.api.get_followers, user_id=user_id, count=5000).pages():
            for follower in page:
                exists = self._check_follower_exists(user_id, follower)
                follower_json = follower._json
                follower_json['messaged'] = False
                if exists:
                    app.logger.debug('Follower {0} exists.'.format(follower.screen_name))
                else:
                    self.db.users.update_one(
                        filter={'user_id': user_id},
                        update={
                            '$addToSet': {'followers': follower_json}
                        },
                        upsert=False
                    )
        app.logger.warning('Got {0} new followers.'.format(len(followers)))

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
        for user in users:
            script = self.sheets.get_script(user['screen_name'])
            if len(script) > 0:
                update = self.db.users.find_one_and_update(
                    filter={'user_id': self.user_id},
                    update={'$set': {'script': script.iat[0]}}
                )
                app.logger.debug("Script update for {0}: {1}".format(user['screen_name'], update))

    def construct_ctas(self, client_handle):
        config_df = self.sheets.get_df()
        client_row = config_df[config_df['Handle'] == client_handle]
        cta_labels = ['CTA 1 Label', 'CTA 2 Label', 'CTA 3 Label']
        cta_urls = ['CTA 1 Url', 'CTA 2 Url', 'CTA 3 Url']
        ctas = []
        app.logger.debug('Client row: {0}'.format(client_row))
        for label_col, url_col in zip(cta_labels, cta_urls):
            alpha = client_row[label_col].str.match('[a-z0-9]+', case=False)
            has_label = len(client_row[label_col].iat[0].strip()) > 0
            has_url = len(client_row[url_col].iat[0].strip()) > 0
            if alpha.all() and has_label and has_url:
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
        self.generate_dm_text(from_userid)
        user = self.db.users.find_one({'user_id': from_userid})
        dm_text = user['script']
        ctas = self.construct_ctas(user['screen_name'])
        try:
            if len(ctas) > 0:
                if ctas[0]:
                    self.api.send_direct_message(to_userid, text=dm_text, ctas=ctas)
            else:
                self.api.send_direct_message(to_userid, text=dm_text)
        except Exception as e:
            app.logger.error(e)
        else:
            result = self.db.users.update_many(
                filter={
                    'user_id': user['user_id'],
                    'followers.id': {'$eq': to_userid}
                },
                update={'$set': {'followers.$.messaged': True}}
            )
            app.logger.debug(result.raw_result)
        app.logger.debug('Sent message from {0} to {1}'.format(
            user['screen_name'],
            to_userid
        ))

    def filter_inactive(self, client, follower):
        filter_df = self.sheets.get_df()
        client_filter = filter_df[filter_df['Handle'] == client]['Minimum Account Age (weeks)'].iat[0]
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
        client_filter = filter_df[filter_df['Handle'] == client]['Minimum Posts'].iat[0]
        if follower['statuses_count'] > int(client_filter):
            return True
        return False

    def filter_follower_count(self, client, follower):
        filter_df = self.sheets.get_df()
        client_filter = filter_df[filter_df['Handle'] == client]['Minimum Followers'].iat[0]
        if follower['followers_count'] > int(client_filter):
            return True
        return False

    def filter_blocked(self, client, follower):
        blocked = True
        try:
            blocklist = self.sheets.get_blocklist(client)
            blocked = blocklist.str.contains(follower['screen_name']).any()
        except Exception as e:
            app.logger.exception(e)
            return False
        return blocked

    def direct_message_all_followers(self):
        user_id = self.user_id
        user = self.db.users.find_one({'user_id': self.user_id})
        self.sheets.update()
        client = user['screen_name']
        for follower in self.get_old_followers(user_id):
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
                app.logger.warning('Message sent to follower: {0}'.format(follower['screen_name']))
            else:
                app.logger.warning(
                    'Follower {0} has been messaged, blocked or filtered out.'.format(follower['screen_name'])
                )
