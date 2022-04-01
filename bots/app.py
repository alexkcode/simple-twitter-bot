import flask, os, secrets, gspread
from datetime import datetime
from flask import Flask, request, g, session, render_template, after_this_request
import logging, tweepy
import twitter, config, sheets
import atexit
import pymongo
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = secrets.token_urlsafe(16)
logging.basicConfig(level=logging.DEBUG)
app.config.from_object('config.Config')

def get_scheduler():
    if not 'scheduler' in g:
        g.scheduler = BackgroundScheduler()
    return g.scheduler

def get_db():
    if not 'db' in g:
        g.db_client = pymongo.MongoClient('mongodb', 27017)
        g.db = g.db_client['twitter']
        g.db.users.create_index(
            [
                ('user_id', pymongo.ASCENDING), 
                ('followers.id', pymongo.ASCENDING)
            ], 
            unique=True
        )
        g.db.sheets.create_index([('sheet_id', pymongo.ASCENDING)],
                                  unique=True)
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

def get_tww():
    if not 'tww' in g:
        pass
        # g.tww = twitter.TwitterWrapper(db=get_db(), api=, user_id=None)
    return g.tww

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
            db_user = {
                'user_id': user.id,
                'screen_name': user.screen_name,
                'token': access_token, 
                'secret': access_token_secret
            }
            if get_db().users.find_one({'user_id': user.id}):
                app.logger.info("Twitter account {0} exists.".format(user.id))
            else:
                app.logger.info(get_db().users.insert_one(db_user))
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

@app.route("/start_job")
def start_job():
    pass

@app.route("/stop_all")
def stop_all():
    pass

@app.route("/test/<screen_name>/<follower>")
def test(screen_name, follower):
    result = get_db().users.find_one(
        filter={
            'screen_name': screen_name,
        },
        update={'$set': {'followers.$[element].messaged': True}},
        array_filters=[{ 'element.screen_name': follower }]
    )
    return result

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
        user_tokens = g.db.users.find_one()
        if len(user_tokens) > 0:
            return "OK"
        else:
            return "NOT AUTHORIZED" 
        # return session['oauth']
    auth = get_auth()
    auth_url = auth.get_authorization_url()
    # g.db.users.insert_one({
    #     "oauth_token": auth.request_token["oauth_token"], 
    #     "oauth_token_secret": auth.request_token["oauth_token_secret"]
    # })
    session['oauth'] = auth.request_token
    return render_template('authorize.html', auth_url=auth_url) 

def job(screen_name):
    try:
        with app.app_context():
            user = get_db().users.find_one({'screen_name':screen_name})
            id = str(user['user_id'])
            app.logger.info('Working on {0} : {1}'.format(user['screen_name'], id))
            auth = tweepy.OAuth1UserHandler(
                app.config['CONSUMER_KEY'], 
                app.config['CONSUMER_SECRET'],
                # Access Token here 
                user['token'],
                # Access Token Secret here
                user['secret']
            )
            api = tweepy.API(auth)
            app.logger.info('VERIFIED {0}'.format(api.verify_credentials().id))
            # tw = twitter.TwitterWrapper(db=get_db(), api=api, user_id=id)
            # tw.get_new_followers()
            tww = twitter.TwitterWrapper(db=get_db(), api=api, sheets=get_shw(), user_id=api.verify_credentials().id)
            # tww.delete_followers()
            tww.get_new_followers()
            app.logger.info(get_shw().get_script(user['screen_name']))
            tww.generate_dm_text(user['user_id'])
            app.logger.info('Follower IDs for {0}: {1}'.format(
                user['screen_name'], 
                tww.get_old_followers(user['user_id'])
            ))
            app.logger.info('Script for {0}: {1}'.format(
                user['user_id'], 
                get_db().users.find_one({'user_id': user['user_id']})['script']
            ))
            # tww.direct_message(tww.get_old_followers(user['user_id'])[0])
            # tww.direct_message_all_followers()
            # user = get_db().users.find_one({'user_id': user['user_id']})
    except Exception as e:
        # app.logger.error(e)
        app.logger.error("TWITTER JOB FAILED at {0}".format(datetime.now()))
        raise e
        # app.logger.info("\n\nAPP TOKEN = %s\n" % app.config['CONSUMER_KEY'])
    else:
        app.logger.info("TWITTER JOB SUCCEEDED")

def check_sheet():
    try:
        with app.app_context():
            get_shw().update()
            for user in get_db().users.find():
                status = get_shw().job_status(user['screen_name']).lower()
                if status == 'start':
                    start_job()
                    get_db().jobs.update_one()
                    get_scheduler().add_job(func=job, trigger="interval", seconds=30)

    except Exception as e:
        app.logger.error("GOOGLE SHEETS CHECK FAILED at {0}".format(datetime.now()))
        app.logger.error(e)
    else:
        app.logger.info("GOOGLE SHEETS CHECK SUCCEEDED")

scheduler = None
with app.app_context():
    scheduler = get_scheduler()
# needs to be around 30 seconds otherwise not enough time to complete spreadsheet creation requests
scheduler.add_job(func=check_sheet, trigger="interval", seconds=60)
scheduler.start(paused=True)

atexit.register(lambda: scheduler.shutdown())

if __name__ == "__main__":
    app.run(port=5000, debug=True)