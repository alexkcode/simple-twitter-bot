import flask, os, secrets, gspread
from datetime import datetime
from flask import Flask, request, g, session, render_template, after_this_request
import logging, tweepy
import twitter, config, sheets
import atexit
import redis
# import pymongo
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = secrets.token_urlsafe(16)
logging.basicConfig(level=logging.DEBUG)
app.config.from_object('config.Config')

def get_db():
    if not 'db' in g:
        g.db = redis.Redis(host='redis')
        # g.db = pymongo.MongoClient('mongodb')
    return g.db

def get_auth():
    if not 'auth' in g:
        g.auth = tweepy.OAuth1UserHandler(
            os.getenv('CONSUMER_KEY'),
            os.getenv('CONSUMER_SECRET'),
            callback="oob")
    return g.auth

def get_gc():
    if not 'gc' in g:
        g.gc = gspread.service_account(filename=app.config['CRED_LOCATION'])
    return g.gc

def get_shw():
    if not 'shw' in g:
        g.shw = sheets.SheetsWrapper(db=get_db(), gc=get_gc())
    return g.shw

@app.before_request
def before_request():
    g.db = get_db()
    g.auth = get_auth()
    app.config.from_object('config.Config')

def verify_pin(auth, pin, user_id="none"):
    access_token, access_token_secret = None, None
    api = None
    try:
        access_token, access_token_secret = auth.get_access_token(pin)
        api = tweepy.API(auth, wait_on_rate_limit=True)
        user = api.verify_credentials()
        app.logger.info("\nProcessing user_id: {0}\n".format(user.id))
        with app.app_context():
            session['user_id'] = user.id
            get_db().sadd('users', user.id)
            get_db().hset('screen_names', user.screen_name, user.id)
            get_db().hmset('user:{0}'.format(user.id), dict(token=access_token, secret=access_token_secret))
    except tweepy.errors.Unauthorized as e:
        app.logger.error(e)
        app.logger.error("Please check your access tokens.")
    except Exception as e:
        app.logger.error("Error creating API", exc_info=True)
        raise e
    else:
        app.logger.info("API created")
    return api

@app.route("/")
def index():
    return "OK"

@app.route("/check/")
def check():
    return "OK"

@app.route("/initalize/")
def initalize():
    gc = get_gc()
    sh = gc.create("test")
    get_db().set("sheet_id", str(sh.id))
    sh.share(app.config['EMAIL1'], perm_type='user', role='writer')
    return "OK"

@app.route("/authorize/", methods=['GET', 'POST'])
def authorize():
    # try:
    if request.method == 'POST':
        pin = request.form['pin']
        auth = get_auth()
        auth.request_token = session['oauth']
        api = verify_pin(
            auth,
            pin)
        user_tokens = g.db.hkeys('user:{0}'.format(session['user_id']))
        if len(user_tokens) > 0:
            return "OK"
        else:
            return "NOT AUTHORIZED" 
        # return session['oauth']
    auth = get_auth()
    auth_url = auth.get_authorization_url()
    g.db.hset('oauth', key=auth.request_token["oauth_token"], value=auth.request_token["oauth_token_secret"])
    session['oauth'] = auth.request_token
    app.logger.info("oauth_token from REDIS: %s" % g.db.hget('oauth', auth.request_token["oauth_token"]))
    return render_template('authorize.html', auth_url=auth_url) 

def job():
    try:
        with app.app_context():
            app.logger.info('USERS {0}'.format(str(get_db().scan(match='user*'))))
            names = get_db().hgetall('screen_names')
            for name in names:
                id = str(names[name], 'utf-8')
                app.logger.info('Working on {0} : {1}'.format(name, id))
                app.logger.info(get_db().hget('user:' + str(id), 'secret'))
                auth = tweepy.OAuth1UserHandler(
                    app.config['CONSUMER_KEY'], 
                    app.config['CONSUMER_SECRET'],
                    # Access Token here 
                    get_db().hget('user:' + str(id), 'token'),
                    # Access Token Secret here
                    get_db().hget('user:' + str(id), 'secret')
                )
                api = tweepy.API(auth)
                app.logger.info('VERIFIED {0}'.format(api.verify_credentials().id))
                tw = twitter.TwitterWrapper(db=get_db(), api=api, user_id=id)
                tw.get_new_followers()
            get_shw().update()
    except Exception as e:
        # app.logger.error(e)
        app.logger.error("JOB FAILED at {0}".format(datetime.now()))
        raise e
        # app.logger.info("\n\nAPP TOKEN = %s\n" % app.config['CONSUMER_KEY'])
    else:
        app.logger.info("JOB SUCCEEDED")

scheduler = BackgroundScheduler()
# needs to be around 30 seconds otherwise not enough time to complete spreadsheet creation requests
scheduler.add_job(func=job, trigger="interval", seconds=20)
scheduler.start()

atexit.register(lambda: scheduler.shutdown())

if __name__ == "__main__":
    app.run(port=5000, debug=True)