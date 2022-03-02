import os
import pymongo
import tweepy
from config import authorize

api = authorize()

def send_direct_message(to_userid):
    first_name = get_username(to_userid).split(' ')[0]
    dm_text = generate_dm_text(first_name)
    api.send_direct_message(to_userid, text=dm_text)