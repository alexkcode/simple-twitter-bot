import tweepy
from flask import Flask, request, redirect, Response, logging
import os, sys
import pymongo

# consumer_token = os.environ['TW_CTOKEN']
# consumer_secret = os.environ['TW_CSECRET']

app = Flask(__name__)

def authorize(auth, verifier):
    access_token, access_token_secret = auth.get_access_token(
        verifier
    )
    api = tweepy.API(auth, wait_on_rate_limit=True)
    try:
        api.verify_credentials()
    except Exception as e:
        app.logger.error("Error creating API", exc_info=True)
        raise e
    app.logger.info("API created")
    return api

class Config(object):

    def __init__(self, consumer_key, consumer_secret) -> None:
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        # self.consumer_key = app.config['TW_CTOKEN']
        # self.consumer_secret = app.config['TW_CSECRET']
        self.access_token = os.environ['TW_ATOKEN']
        self.access_token_secret = os.environ['TW_ASECRET']
        app.config['TW_ATOKEN'] = self.access_token
        app.config['TW_ASECRET'] = self.access_token_secret

    def authorize(self):
        auth = tweepy.OAuthHandler(self.consumer_key, self.consumer_secret)
        auth.set_access_token(self.access_token, self.access_token_secret)
        api = tweepy.API(auth, wait_on_rate_limit=True,
                        wait_on_rate_limit_notify=True)
        try:
            api.verify_credentials()
        except Exception as e:
            app.logger.error("Error creating API", exc_info=True)
            raise e
        app.logger.info("API created")
        return api

    @staticmethod
    def get_language():
        try:
            twitter_lang = os.environ['TWITTER_LANG'].split(',')
        except ValueError:
            twitter_lang = ['en']
        return twitter_lang

    
    # def authorize(consumer_key, consumer_secret, auth, verifier):
    # auth contains consumer key and secret already