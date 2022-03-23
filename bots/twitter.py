import os
from flask import Flask
import tweepy
import config

app = Flask(__name__)

class TwitterWrapper(object):

    def __init__(self, db, api:tweepy.API) -> None:
        self.db = db
        self.api = api

    def get_new_followers(self, user_id):
        ids = []
        for page in tweepy.Cursor(self.api.get_follower_ids, user_id=user_id).pages():
            ids.extend(page)
        print(len(ids))
        return ids

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
        coll = self.db["followers"]
        coll.update_one({"username":username},
                        {"$set": {"username":username, "followers":followers_list}},
                        upsert=True)

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