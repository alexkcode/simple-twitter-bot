import tweepy
from flask import Flask, request, redirect, Response, logging
import os, sys
import pymongo

consumer_token = os.environ['TW_CTOKEN']
consumer_secret = os.environ['TW_CSECRET']

logger = logging.getLogger()

app = Flask(__name__)

app.config['TW_ATOKEN'] = os.environ['TW_ATOKEN']
app.config['TW_ASECRET'] = os.environ['TW_ASECRET']

class Config(object):

    def __init__(self, consumer_token, consumer_secret) -> None:
        self.consumer_key = consumer_token
        self.consumer_secret = consumer_secret
        self.access_token = app.config['TW_ATOKEN']
        self.access_token_secret = app.config['TW_ASECRET']

    def authorize(self):
        auth = tweepy.OAuthHandler(self.consumer_key, consumer_secret)
        auth.set_access_token(self.access_token, self.access_token_secret)
        api = tweepy.API(auth, wait_on_rate_limit=True,
                        wait_on_rate_limit_notify=True)
        try:
            api.verify_credentials()
        except Exception as e:
            logger.error("Error creating API", exc_info=True)
            raise e
        logger.info("API created")
        return api

    @staticmethod
    def get_language():
        try:
            twitter_lang = os.environ['TWITTER_LANG'].split(',')
        except ValueError:
            twitter_lang = ['en']
        return twitter_lang

    