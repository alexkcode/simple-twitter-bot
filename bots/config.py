import tweepy
from flask import Flask, request, redirect, Response, logging
import os, sys
import pymongo
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

def authorize(consumer_key, consumer_secret, auth, verifier):
    # auth = tweepy.OAuth1UserHandler(consumer_key, consumer_secret)
    # print(auth.get_authorization_url())
    # verifier = input("Input PIN: ")
    access_token, access_token_secret = auth.get_access_token(
        verifier
    )
    # auth = tweepy.OAuth1UserHandler(
    #     consumer_key, 
    #     consumer_secret,
    #     access_token,
    #     access_token_secret
    # )
    api = tweepy.client(auth, wait_on_rate_limit=True)
    try:
        api.verify_credentials()
    except Exception as e:
        app.logger.error("Error creating API", exc_info=True)
        raise e
    app.logger.info("API created")
    return api

class Config(object):
    ACCESS_TOKEN = os.getenv('ACCESS_TOKEN')
    ACCESS_TOKEN_SECRET = os.getenv('ACCESS_TOKEN_SECRET')
    CONSUMER_KEY = os.getenv('CONSUMER_KEY')
    CONSUMER_SECRET = os.getenv('CONSUMER_SECRET')

    SCOPES = [
        'https://www.googleapis.com/auth/spreadsheets.readonly',
        'https://www.googleapis.com/auth/drive'
    ]

    def __init__(self, consumer_key, consumer_secret) -> None:
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        # self.access_token = os.getenv('ACCESS_TOKEN')
        # self.access_token_secret = os.getenv('ACCESS_TOKEN_SECRET')
        # self.consumer_key = app.config['TW_CTOKEN']
        # self.consumer_secret = app.config['TW_CSECRET']
        # self.access_token = os.environ['TW_ATOKEN']
        # self.access_token_secret = os.environ['TW_ASECRET']
        # app.config['TW_ATOKEN'] = self.access_token
        # app.config['TW_ASECRET'] = self.access_token_secret

    