import os
from flask import Flask
import pymongo
import tweepy
import config

# config = config.Config()
# api = config.authorize()
# client = pymongo.MongoClient(db_url)

app = Flask(__name__)

def get_new_followers(username):
    ids = []
    for page in tweepy.Cursor(api.followers_ids, screen_name=username).pages():
        ids.extend(page)
    print(len(ids))
    return ids

def seed_db(username):
    o = get_old_followers(username)
    if not o:
        n = get_new_followers(username)
        save_followers(username, n)

def get_old_followers(username):
    ids = []
    db = client.get_default_database()
    coll = db["followers"]
    try:
        for i in coll.find({"username":username}):
            ids = i['followers']
    except:
        ids = []
    print(len(ids))
    return ids

def save_followers(username, followers_list):
    db = client.get_default_database()
    coll = db["followers"]
    coll.update_one({"username":username},
                    {"$set": {"username":username, "followers":followers_list}},
                    upsert=True)

def get_username(ids):
    # auth.set_access_token(access_token, access_token_secret)
    # api = tweepy.API(auth)
    user_data = user = api.get_user(ids)
    return user_data.name

def send_direct_message(api, to_userid):
    first_name = get_username(to_userid).split(' ')[0]
    dm_text = generate_dm_text(first_name)
    api.send_direct_message(to_userid, text=dm_text)