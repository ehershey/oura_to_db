#!/usr/bin/env python3
import datetime
import dateutil
import jsonify
import os
import sys
from flask import Flask, request
import pprint
import sentry_sdk
import oura_to_db
from sentry_sdk.integrations.flask import FlaskIntegration


sentry_sdk.init(
    traces_sample_rate=1.0,
    profiles_sample_rate=1.0,
    enable_tracing=True,
    integrations=[FlaskIntegration(),],
)

required_env_vars = [
    "SENTRY_DSN",
    "OURA_TOKEN",
    "OURA_MONGODB_URI",
]
missing_required_env_var = False
for var in required_env_vars:
    if var not in os.environ:
        print(f"missing required environment variable: {var}")
        missing_required_env_var = True
if missing_required_env_var:
    sys.exit(1)

app = Flask(__name__)


@app.route("/")
def hello_world():
    pprint.pprint(request.url)
    return "<p>Hello, World!</p>"


@app.route("/ping")
def ping():
    pprint.pprint(request.url)
    return {
        "mongodb": oura_to_db.mongodb_ping(),
        "oura": oura_to_db.oura_ping(),
    }


@app.route('/run')
@app.route("/run/<path:date>")
def run(date=None):
    pprint.pprint(request.url)
    end_date_string = date
    start_date_string = date
    print(f"date: {date}")
    days_back = 3
    end_date = None
    if date is None:
        print("no date passed in")
        end_date = datetime.datetime.now() + datetime.timedelta(days=1)
    else:
        try:
            parsed_date = dateutil.parser.parse(date)
        except Exception:
            return '', 500
        print(f"parsed_date: {parsed_date}")
        end_date = parsed_date + datetime.timedelta(days=1)

    start_date = end_date - datetime.timedelta(days=days_back)
    start_date_string = str(start_date.date())
    end_date_string = str(end_date.date())
    # return str(dir(oura_to_db) ) + " / " +
    # str(dir(__import__("oura_to_db")) ) +
    # " / " + str(__import__("oura_to_db").__file__)

    # processed_dates, processed_count, inserted_count, modified_count = 
    resp = oura_to_db.run(
        end_date_string=end_date_string,
        start_date_string=start_date_string)
    return_string = ''
    for date in resp["processed_dates"]:
        return_string = return_string + str(date) + "\n"
    return_string = return_string
    return return_string


@app.errorhandler(404)
def handle_404(e):
    pprint.pprint(e)
    pprint.pprint(request.url)
    return '', 404


if __name__ == "__main__":
    print(" in serve.py main block")
    app.run()
