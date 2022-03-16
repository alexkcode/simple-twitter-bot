from flask import Flask
import logging, os, tweepy
import followers
import config
import atexit
import redis
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

logging.basicConfig(level=logging.DEBUG)
# logger = logging.getLogger(__name__)
app.config.from_object('config.Config')
# client = pymongo.MongoClient("mongodb", 27017)

auth = tweepy.OAuth1UserHandler(app.config['CONSUMER_KEY'], app.config['CONSUMER_SECRET'], callback="oob")
api = None

def job():
    try:
        if app.config['verified']:
            app.logger.info("Success")
            # followers.get_new_followers()
            r = redis.Redis(host='redis')
            app.logger.info(r.ping())
    except:
        if not app.config['verified']:
            app.logger.info("Not verified")
        app.logger.info("Failed")
    # app.logger.info("\n\nAPP TOKEN = %s\n" % app.config['CONSUMER_KEY'])

scheduler = BackgroundScheduler()
scheduler.add_job(func=job, trigger="interval", seconds=10)
scheduler.start()

@app.route("/")
def index():
    return auth.get_authorization_url()
    # return "OK"

@app.route("/authorize/<pin>")
def authorize(pin):
    api = config.authorize(
        # app.config['CONSUMER_KEY'], 
        # app.config['CONSUMER_SECRET'], 
        auth, 
        pin
    )
    if api:
        app.config['verified'] = True
        return "VERIFIED"
    else:
        return "NOT VERIFIED"

atexit.register(lambda: scheduler.shutdown())

if __name__ == "__main__":
    app.run(port=5000, debug=True)