import os
from flask import Flask
import tweepy
import config
from app import get_db

app = Flask(__name__)

def get_new_followers(user_id, api:tweepy.API):
    ids = []
    for page in tweepy.Cursor(api.get_follower_ids, user_id=user_id).pages():
        ids.extend(page)
    print(len(ids))
    return ids

def seed_db(username):
    old = get_old_followers(username)
    if not old:
        new = get_new_followers(username)
        save_followers(username, new)

def get_old_followers(username):
    ids = []
    db = get_db()
    coll = db["followers"]
    try:
        for i in coll.find({"username":username}):
            ids = i['followers']
    except:
        ids = []
    print(len(ids))
    return ids

def save_followers(username, followers_list):
    db = get_db()
    coll = db["followers"]
    coll.update_one({"username":username},
                    {"$set": {"username":username, "followers":followers_list}},
                    upsert=True)

def get_username(ids):
    # auth.set_access_token(access_token, access_token_secret)
    # api = tweepy.API(auth)
    user_data = user = api.get_user(ids)
    return user_data.name

def generate_dm_text():
    """
    Generate DM text based on script from Google Drive
    """
    pass

def send_direct_message(api, to_userid):
    first_name = get_username(to_userid).split(' ')[0]
    dm_text = generate_dm_text(first_name)
    api.send_direct_message(to_userid, text=dm_text)