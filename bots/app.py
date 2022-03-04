from flask import Flask
import dm_followers
import atexit
from apscheduler.schedulers.background import BackgroundScheduler

application = Flask(__name__)

@application.route("/")
def index():
    return ""

def job():
    print("Success")

scheduler = BackgroundScheduler()
scheduler.add_job(func=job, trigger="interval", seconds=60)
scheduler.start()

atexit.register(lambda: scheduler.shutdown())

if __name__ == "__main__":
    application.run(port=5000, debug=True)