import flask, os, secrets, gspread
from flask import Flask, request, g, session, render_template, after_this_request
import logging, tweepy
import twitter, config, sheets
import atexit
import redis
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
    return g.db

def get_auth():
    if not 'auth' in g:
        g.auth = tweepy.OAuth1UserHandler(
            os.getenv('CONSUMER_KEY'),
            os.getenv('CONSUMER_SECRET'),
            callback="oob")
    return g.auth

@app.before_request
def before_request():
    g.db = get_db()
    g.auth = get_auth()
    app.config.from_object('config.Config')

def verify_pin(auth, pin, user_id="none"):
    access_token, access_token_secret = None, None
    # g.db = get_db()
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
    g.gc = gspread.service_account(filename=app.config['CRED_LOCATION'])
    sh = g.gc.create("test")
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
    # except Exception as e:
    #     print(e)
    #     app.logger.error(str(e))
    #     return render_template('authorize.html', error=e)

def job():
    try:
        with app.app_context():
            app.logger.info('USERS %s' % str(get_db().scan(match='user*')))
            names = get_db().hgetall('screen_names')
            for name in names:
                id = str(names[name], 'utf-8')
                app.logger.info('Working on {0} : {1}'.format(name, id))
                app.logger.info(get_db().hget('user:' + str(id), 'secret'))
                auth = tweepy.OAuth1UserHandler(
                    app.config['CONSUMER_KEY'], 
                    app.config['CONSUMER_SECRET'],
                    # Access Token here 
                    (get_db().hget('user:' + str(id), 'token')),
                    # Access Token Secret here
                    (get_db().hget('user:' + str(id), 'secret'))
                )
                api = tweepy.API(auth)
                app.logger.info('VERIFIED {0}'.format(api.verify_credentials().id))
                # test = followers.get_new_followers(id, api)
                # app.logger.info(test)
            # app.logger.info(test)
            # if len(users) > 0:
            #     app.logger.info("Success")
            #     # followers.get_new_followers()
            # else:
            #     app.logger.info("Not verified")
    except Exception as e:
        app.logger.error(e)
        app.logger.info("Failed")
    # app.logger.info("\n\nAPP TOKEN = %s\n" % app.config['CONSUMER_KEY'])

scheduler = BackgroundScheduler()
scheduler.add_job(func=job, trigger="interval", seconds=5)
scheduler.start()

atexit.register(lambda: scheduler.shutdown())

if __name__ == "__main__":
    app.run(port=5000, debug=True)