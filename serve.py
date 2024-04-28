#!/usr/bin/env python3
import os
import sys
from flask import Flask, request
import oura_to_db
import pprint
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration


sentry_sdk.init(
    traces_sample_rate=1.0,
    profiles_sample_rate=1.0,
    enable_tracing=True,
    integrations = [ FlaskIntegration(), ],
    debug = True,
)

required_env_vars = [
    "SENTRY_DSN",
    "OURA_TOKEN",
    "OURA_MONGODB_URI",
    "REQUIRED_BEARER",
    "TAILSCALE_AUTHKEY"
]
missing_required_env_var = False
for var in required_env_vars:
    if var not in os.environ:
        print(f"missing required environment variable: {var}")
        missing_required_env_var = True
if missing_required_env_var:
    sys.exit(1)
# required env vars


app = Flask(__name__)

@app.route("/")
def hello_world():
        return "<p>Hello, World!</p>"

@app.route("/run")
def run():
        return dir(oura_to_db)

@app.errorhandler(404)
def handle_404(e):
    pprint.pprint(e)
    pprint.pprint(request.url)
    # handle all other routes here
    return 'Not Found, but we HANDLED IT'
# app.run()
#@app.route('/', defaults={'path': ''})
#@app.route('/<path:path>')
#def catch_all(path):
    #print(f"You want path: {path}")
    #return '', 404
