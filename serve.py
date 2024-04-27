#!/usr/bin/env python3

required_env_vars = ["SENTRY_DSN", "OURA_CLIENT_ID", "OURA_SECRET_ID", "OURA_MONGODB_URI", "REQUIRED_BEARER"]
missing_required_env_var = False
for var in required_env_vars:
    if var not in os.environ:
        print("missing required environment variable: {var}")
        missing_required_env_var = True
if missing_required_env_var:
    os.exit(1)
# required env vars
