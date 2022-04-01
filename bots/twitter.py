import os, json
from re import U
from flask import Flask
import tweepy
import config
import sheets

app = Flask(__name__)

class TwitterWrapper(object):

    def __init__(self, db, api:tweepy.API, sheets:sheets.SheetsWrapper, user_id=None) -> None:
        self.db = db
        self.api = api
        self.user_id = user_id
        self.sheets = sheets

    def delete_followers(self, user_id=None):
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
                self.db.users.find_one_and_update(
                    filter={'user_id': user_id},
                    update={'$addToSet': {'followers': follower._json}}
                )
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
        except Exception as e:
            raise e
        return ids

    def save_followers(self, username, followers_list):
        pass
        # coll = self.db["followers"]
        # coll.update_one({"username":username},
        #                 {"$set": {"username":username, "followers":followers_list}},
        #                 upsert=True)

    def get_username(self, ids, api):
        pass
        # auth.set_access_token(access_token, access_token_secret)
        # api = tweepy.API(auth)
        # user = api.get_user(ids)
        # return user_data.name

    def generate_dm_text(self, user_id=None):
        """
        Generate DM text based on script from Google Drive
        """
        users = None 
        if user_id:
            users = self.db.users.find() 
        else:
            users = self.db.users.find_one({'user_id':user_id})
        for user in users:
            script = self.sheets.get_script(user['screen_name'])
            self.db.users.find_one_and_update(
                filter={'user_id': self.user_id},
                # update={'$set': {'script': script.to_string(index=False)}}
                update={'$set': {'script': script[0]}}
            )

    def direct_message(self, to_userid):
        # first_name = self.get_username(to_userid).split(' ')[0]
        self.generate_dm_text(to_userid)
        user = self.db.users.find_one({'user_id': self.user_id})
        dm_text = user['script']
        ctas=[
          {
            "type": "web_url",
            "label": "Test CTA One",
            "url": "https://www.upliftcampaigns.com/"
          },
          {
            "type": "web_url",
            "label": "Test CTA Two",
            "url": "https://twitter.com/"
          }
        ]
        # self.api.send_direct_message(to_userid, text=dm_text, ctas=ctas)
        self.db.users.update_many(
            filter={
                'user_id': self.user_id,
                # 'followers.id': {'$eq': to_userid}
            },
            update={'$set': {'followers.$[element].messaged': True}},
            array_filters=[{ 'element.id': to_userid }]
        )
        app.logger.info('Sent message from {0} to {1}'.format(
            user['screen_name'],
            to_userid
        ))

    def direct_message_all_followers(self):
        user_id = self.user_id
        for follower_id in self.get_old_followers(user_id):
            self.direct_message(follower_id)
