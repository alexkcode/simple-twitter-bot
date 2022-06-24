import flask, os, secrets, gspread
from datetime import datetime
from pytz import timezone
from flask import Flask, request, g, session, render_template, redirect
import logging, tweepy
import twitter, config, sheets
import atexit
import pymongo
import apscheduler
from apscheduler.schedulers.background import BackgroundScheduler
from flask_apscheduler import APScheduler
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = secrets.token_urlsafe(16)
app.config.from_object('config.Config')

LOG_FORMAT = ('%(levelname) -10s %(asctime)s %(name) -30s %(funcName) '
              '-35s %(lineno) -5d: %(message)s')
fh = logging.handlers.TimedRotatingFileHandler('error.log', when='D', interval=1)
logging.basicConfig(
    level=logging.WARNING, 
    format=LOG_FORMAT,
    datefmt='%m-%d-%y %H:%M:%S',
    handlers=[fh]
)

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
                ('user_id', pymongo.ASCENDING)
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

def get_tww(screen_name):
    user = get_db().users.find_one({'screen_name': screen_name})
    auth = tweepy.OAuth1UserHandler(
        app.config['CONSUMER_KEY'], 
        app.config['CONSUMER_SECRET'],
        # Access Token here 
        user['token'],
        # Access Token Secret here
        user['secret']
    )
    api = tweepy.API(auth)
    return twitter.TwitterWrapper(
        db=get_db(), 
        api=api, 
        sheets=get_shw(), 
        user_id=api.verify_credentials().id
    )

scheduler = None
with app.app_context():
    scheduler = get_scheduler()

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
                'secret': access_token_secret,
                'followers': []
            }
            result = get_db().users.update_one(
                filter={'user_id': user.id},
                update={
                    '$setOnInsert': db_user
                },
                upsert=True
            )
            app.logger.info("Twitter account {0}: {1}".format(user.id, result))
    except tweepy.errors.Unauthorized as e:
        app.logger.error(e)
        app.logger.error("Please check your access tokens.")
    except Exception as e:
        app.logger.error("Error creating API", exc_info=True)
        raise e
    else:
        app.logger.info("API created")
    return api

def job(screen_name):
    try:
        with app.app_context():
            app.logger.warning("TWITTER JOB FOR {0} STARTING ...".format(screen_name))
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
            tww = twitter.TwitterWrapper(db=get_db(), api=api, sheets=get_shw(), user_id=api.verify_credentials().id)
            # tww.delete_followers(user_id=user['user_id'])
            tww.get_new_followers()
            tww.sheets.update()
            tww.generate_dm_text(user['user_id'])
            app.logger.debug('Follower IDs for {0}: {1}'.format(
                user['screen_name'], 
                tww.get_old_followers(user['user_id'])
            ))
            app.logger.debug('Script for {0}: {1}'.format(
                user['user_id'], 
                get_db().users.find_one({'user_id': user['user_id']})['script']
            ))
            tww.direct_message_all_followers()
    except Exception as e:
        # app.logger.error(e)
        app.logger.error("TWITTER JOB FAILED at {0}".format(datetime.now()))
        app.logger.error(e)
        raise e
        # app.logger.info("\n\nAPP TOKEN = %s\n" % app.config['CONSUMER_KEY'])
    else:
        app.logger.warning("TWITTER JOB FOR {0} SUCCEEDED".format(screen_name))

@app.route("/start_job/<user_id>")
def start_job(user_id):
    with app.app_context():
        user = get_db().users.find_one(
            filter={
                'user_id': user_id
            }
        )
        running_job = get_db().jobs.find_one(
            filter={
                'user_id': user_id
            }
        )
        message = ''
        if running_job:
            message = 'JOB FOR TWITTER USER {0} EXISTS.\n{1}'.format(
                user['screen_name'],
                running_job
            )
        else:
            scheduled_job = scheduler.add_job(
                func=job, 
                replace_existing=True,
                kwargs={'screen_name': user['screen_name']},
                trigger='cron', 
                # day_of_week='mon-fri', 
                # 9 AM to 9 PM
                hour='9-21', 
                minute='0-59/2',
                start_date=datetime.now(timezone('America/New_York')),
                timezone=timezone('America/New_York'),
                id=user['screen_name']
            )
            app.logger.info('Current jobs: {0}'.format(scheduler.get_jobs()))
            get_db().jobs.find_one_and_update(
                filter={
                    'user_id': user_id
                },
                update={
                    '$set': {
                        'user_id': user_id,
                        'job_id': scheduled_job.id
                    }
                },
                upsert=True
            )
            message = 'ADDED JOB FOR TWITTER {0}'.format(scheduled_job)
        app.logger.warning(message)
    return message

@app.route("/stop_job/<user_id>")
def stop_job(user_id):
    filter = {'user_id': user_id}
    db_job = get_db().jobs.find_one(filter)
    user = get_db().users.find_one(filter)
    existing_job = None
    try:
        if db_job:
            existing_job = scheduler.get_job(db_job['job_id'])
        app.logger.info('EXISTING JOB : {0}'.format(existing_job))
        deleted_job = get_db().jobs.find_one_and_delete(filter)
        removed_job = None
        if existing_job:
            removed_job = scheduler.remove_job(db_job['job_id'])
        app.logger.warning(
            'Removed job {0} for user {1}'.format(
                removed_job, 
                user['screen_name']
            )
        )
    except Exception as e:
        app.logger.warning(
            'No jobs to remove for user {0}. {1}'.format(user['screen_name'], e)
        )

@app.route("/delete_followers/<screen_name>")
def delete_followers(screen_name):
    try:
        app.logger.warning('Deleting followers for {0}'.format(screen_name))
        tww = get_tww(screen_name)
        tww.delete_followers(screen_name=screen_name)
        tww.sheets.update()
        app.logger.warning('Followers for {0} deleted'.format(screen_name))
    except Exception as e:
        return "User {0} not found.\n{1}".format(screen_name, e)
    else:
        return "Removed followers for {0} from the database.".format(screen_name)

@app.route("/delete_client/<screen_name>")
def delete_client(screen_name):
    try:
        user = get_db().users.find_one({'screen_name':screen_name})
        deleted_user = get_db().users.find_one_and_delete({'user_id': user['id']})
    except Exception as e:
        return "User {0} not found.\n{1}".format(screen_name, e)
    else:
        return "Removed client {0} from the database.".format(deleted_user['screen_name'])

@app.route("/set_messaged/<screen_name>/<follower>")
def set_messaged(screen_name, follower):
    result = get_db().users.find_one_and_update(
        filter={
            'screen_name': screen_name,
        },
        update={'$set': {'followers.$[element].messaged': True}},
        array_filters=[{ 'element.screen_name': follower }],
        return_document=pymongo.ReturnDocument.AFTER
    )
    return result

@app.route("/authorize/", methods=['GET', 'POST'])
def authorize():
    if request.method == 'POST':
        pin = request.form['pin']
        auth = get_auth()
        auth.request_token = session['oauth']
        api = verify_pin(
            auth,
            pin)
        user_tokens = g.db.users.find_one()
        if len(user_tokens) > 0:
            return "AUTHORIZED"
        else:
            return "NOT AUTHORIZED" 
    auth = get_auth()
    auth_url = auth.get_authorization_url()
    session['oauth'] = auth.request_token
    return render_template('authorize.html', auth_url=auth_url) 

def check_sheet():
    try:
        app.logger.warning("STARTING GOOGLE SHEETS CHECK")
        with app.app_context():
            get_shw().update()
            for user in get_db().users.find():
                status = None
                try:
                    status = get_shw().job_status(user['screen_name']).iat[0]
                    app.logger.info('Job status : {0}'.format(status))
                except Exception as e:
                    app.logger.error(
                        'Job status for clients not found or no clients found. \n{0}'.format(e)
                    )
                    stop_job(user['user_id'])
                else:
                    if status == 'start':
                        start_job(user['user_id'])
                    elif status == 'reset':
                        stop_job(user['user_id'])
                        delete_followers(user['screen_name'])
                    else:
                        stop_job(user['user_id'])
            scheduler.print_jobs()
    except Exception as e:
        app.logger.error("GOOGLE SHEETS CHECK FAILED at {0}".format(datetime.now()))
        raise(e)
    else:
        app.logger.warning("GOOGLE SHEETS CHECK SUCCEEDED")

def start_scheduler():
    try:
        scheduler.start(paused=False)
        scheduler.add_job(
            func=check_sheet, 
            trigger="interval", 
            seconds=30,
            start_date=datetime.now()
        )
    except Exception as e:
        with app.app_context():
            app.logger.error(e)
    finally:
        return "JOB SCHEDULER RESTARTED"

@app.route("/stop_all")
def stop_all():
    try:
        deleted_job = get_db().jobs.delete_many({})
        scheduler.shutdown()
    except Exception as e:
        return "NO JOBS TO DELETE.\n{0}".format(e)
    else:    
        return "ALL JOBS STOPPED AND DELETED. JOB SCHEDULER HAS STOPPED."

# needs to be around 30 seconds otherwise not enough time to complete spreadsheet creation requests
scheduler.add_job(
    func=check_sheet, 
    trigger="interval", 
    seconds=30,
    start_date=datetime.now()
)
scheduler.start(paused=False)

@app.route("/", methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if request.form['submit_button'] == 'STOP ALL JOBS':
            return stop_all()
        if request.form['submit_button'] == 'CURRENT JOBS':
            jobs = []
            try:
                for job in get_db().jobs.find({}):
                    user = get_db().users.find_one({'user_id': job['user_id']})
                    job['handle'] = user['screen_name']
                    jobs.append(job)
            except Exception as e:
                app.logger.error('Error when checking current jobs: {0}'.format(e))
            return 'Current jobs: {0}'.format(jobs)
        if request.form['submit_button'] == 'AUTHORIZE NEW CLIENT':
            return redirect('/authorize/') 
    return render_template('index.html')

atexit.register(lambda: scheduler.shutdown())

if __name__ == "__main__":
    app.run(port=5000, debug=False)