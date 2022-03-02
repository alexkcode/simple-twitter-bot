import tweepy
import logging
import os
import sys
import pymongo

consumer_token = os.environ['TW_CTOKEN']
consumer_secret = os.environ['TW_CSECRET']
access_token = os.environ['TW_ATOKEN']
access_token_secret = os.environ['TW_ASECRET']

logger = logging.getLogger()

def authorize():
    consumer_key = CONSUMER_KEY
    consumer_secret = CONSUMER_SECRET
    access_token = ACCESS_TOKEN
    access_token_secret = ACCESS_TOKEN_SECRET

    auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
    auth.set_access_token(access_token, access_token_secret)
    api = tweepy.API(auth, wait_on_rate_limit=True,
                     wait_on_rate_limit_notify=True)
    try:
        api.verify_credentials()
    except Exception as e:
        logger.error("Error creating API", exc_info=True)
        raise e
    logger.info("API created")
    return api

class Config(object):

    @staticmethod
    def get_language():
        try:
            twitter_lang = os.environ['TWITTER_LANG'].split(',')
        except ValueError:
            twitter_lang = ['en']
        return twitter_lang

    