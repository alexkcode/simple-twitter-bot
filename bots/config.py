import tweepy
from flask import Flask, request, redirect, Response, logging, g
import os
import redis
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

class Config(object):
    ACCESS_TOKEN = os.getenv('ACCESS_TOKEN')
    ACCESS_TOKEN_SECRET = os.getenv('ACCESS_TOKEN_SECRET')
    CONSUMER_KEY = os.getenv('CONSUMER_KEY')
    CONSUMER_SECRET = os.getenv('CONSUMER_SECRET')
    BEARER_TOKEN = os.getenv('BEARER_TOKEN')
    EMAIL1 = os.getenv('EMAIL1')
    # make sure to update this!
    CRED_LOCATION = 'service_account_token.json'

    SCOPES = [
        'https://www.googleapis.com/auth/spreadsheets.readonly',
        'https://www.googleapis.com/auth/drive'
    ]