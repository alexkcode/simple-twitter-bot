from flask import Flask
import logging, os, tweepy
import dm_followers
import config
import atexit
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

logging.basicConfig(level=logging.DEBUG)
# logger = logging.getLogger(__name__)
app.config.from_object('config.Config')
auth = tweepy.OAuth1UserHandler(app.config['CONSUMER_KEY'], app.config['CONSUMER_SECRET'], callback="oob")

def job():
    try:
        if app.config['verified']:
            app.logger.info("Success")
            app.logger.info()
    except:
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
        app.config['api'] = api
        return "VERIFIED"
    else:
        return "NOT VERIFIED"

atexit.register(lambda: scheduler.shutdown())

if __name__ == "__main__":
    app.run(port=5000, debug=True)