import os
from flask import Flask
import tweepy
import config

app = Flask(__name__)

class TwitterWrapper(object):

    def __init__(self, db, api:tweepy.API, user_id=None) -> None:
        self.db = db
        self.api = api
        self.user_id = user_id

    def get_new_followers(self, user_id=None) -> None:
        if not user_id:
            user_id = self.user_id
        followers = {}
        for page in tweepy.Cursor(self.api.get_followers, user_id=user_id).pages():
            for follower in page:
                followers[follower.id] = follower
            app.logger.info(followers)
        # self.db.hmset("followers:{0}".format(user_id), followers)
        app.logger.info("Got {0} followers.".format(len(followers)))

    def seed_db(self, username):
        old = self.get_old_followers(username)
        if not old:
            new = self.get_new_followers(username)
            self.save_followers(username, new)

    def get_old_followers(self, username):
        ids = []
        coll = self.db["followers"]
        try:
            for i in coll.find({"username":username}):
                ids = i['followers']
        except:
            ids = []
        print(len(ids))
        return ids

    def save_followers(self, username, followers_list):
        pass
        # coll = self.db["followers"]
        # coll.update_one({"username":username},
        #                 {"$set": {"username":username, "followers":followers_list}},
        #                 upsert=True)

    def get_username(self, ids, api):
        # auth.set_access_token(access_token, access_token_secret)
        # api = tweepy.API(auth)
        user_data = user = api.get_user(ids)
        return user_data.name

    def generate_dm_text(self):
        """
        Generate DM text based on script from Google Drive
        """
        pass

    def send_direct_message(self, to_userid):
        first_name = self.get_username(to_userid).split(' ')[0]
        dm_text = self.generate_dm_text(first_name)
        self.api.send_direct_message(to_userid, text=dm_text)