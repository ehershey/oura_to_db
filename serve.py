#!/usr/bin/env python3
import os
import sys
from flask import Flask

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

# app.run()
