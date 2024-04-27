#!/usr/bin/env python3
"""
Download Oura activity data and save in database
"""

import argparse
import sys
import dateutil
import logging
import os
# import erniemail
import erniegps
import erniegps.db
from pymongo import MongoClient
# from oura import OuraClient, OuraOAuth2Client
from oura import OuraOAuth2Client
from oura.v2 import OuraClientV2
from types import SimpleNamespace
import pickle
import pprint
import pytz
import pymongo
import time
import datetime


import sentry_sdk
from sentry_sdk.integrations.pymongo import PyMongoIntegration

sentry_sdk.init(
    # Set traces_sample_rate to 1.0 to capture 100%
    # of transactions for performance monitoring.
    traces_sample_rate=1.0,
    # Set profiles_sample_rate to 1.0 to profile 100%
    # of sampled transactions.
    # We recommend adjusting this value in production.
    profiles_sample_rate=1.0,
    enable_tracing=True,
    integrations = [ PyMongoIntegration(), ],
)

autoupdate_version = 167

DB_URL = erniegps.db.get_db_url("oura")
#if "MONGODB_URI" in os.environ:
    #DB_URL = os.environ["MONGODB_URI"]
#else:
    #DB_URL = 'mongodb://localhost:27017/'

DB_NAME = 'oura'
COLLECTION_NAME = 'activity'

#CLIENT_ID = xxxxx
#CLIENT_SECRET = 'xxx'

# GET FROM https://cloud.ouraring.com/oauth/applications/xxx

#OURA_CLIENT_ID = "xxx"
#OURA_TOKEN = "xxx" # retired 2022-11-27
OURA_TOKEN = "xxx" # inserted 2022-11-27
#OURA_CLIENT_SECRET = "xxx"

PICKLE_FILE = os.environ['HOME'] + "xxx"

#ACTIVITY_VERSION = 0.1
ACTIVITY_VERSION = 0.2  # change timestamps to date objects
#ACTIVITY_VERSION = 0.3  # Add map

PROCESSED_DATES = {}


@sentry_sdk.trace
def get_args():
    """ Parse command line args """
    parser = argparse.ArgumentParser(
        description='Store Oura activity data in db')
    parser.add_argument(
        '--days_back',
        required=False,
        default=3,
        help='Number of days back to search Oura',
        type=int)
    parser.add_argument(
        '--date',
        required=False,
        default=None,
        help='Date to search',
        type=datetime.date.fromisoformat)
    parser.add_argument(
        '--oauth_code',
        required=False,
        help='Code for oauth to skip initial auth request and prompt',
        type=str)
    parser.add_argument(
        '--force_reauth',
        default=False,
        help='Re-auth to Oura',
        action='store_true')
    parser.add_argument(
        '--verbose',
        default=False,
        help='Print (slight) verbose info to stdout',
        action='store_true')
    parser.add_argument(
        '--debug',
        default=False,
        help='Print debugging info to stderr',
        action='store_true')
    args = parser.parse_args()
    return args


@sentry_sdk.trace
def save_pickle(config_data={}):
    with open(PICKLE_FILE, 'wb') as f:
        pickle.dump(config_data, f)


@sentry_sdk.trace
def load_pickle():
    with open(PICKLE_FILE, 'rb') as f:
        config_data = pickle.load(f)
    return config_data


@sentry_sdk.trace
def setup_pickle():
    if os.path.exists(PICKLE_FILE):
        logging.debug("found pickle file, loading it")
        return load_pickle()
    else:
        logging.debug("No pickle file, creating it")
        save_pickle()
        return {}

# {'token_type': 'bearer', 'refresh_token': <refresh>, 'access_token': <token>, 'expires_in': 86400, 'expires_at': 1546485086.3277025}
@sentry_sdk.trace
def handle_auth_callback(token_dict):
    logging.debug("got token_dict in refresh_callback")
    logging.debug(f"token_dict: {token_dict}")
    pickle_data = setup_pickle()
    logging.debug("loaded/initialized pickle")
    logging.debug(f"pickle_data: {pickle_data}")
    pickle_data['refresh_token'] = token_dict['refresh_token']
    pickle_data['access_token'] = token_dict['access_token']
    pickle_data['expires_in'] = token_dict['expires_in']
    pickle_data['expires_at'] = token_dict['expires_at']
    save_pickle(pickle_data)
    logging.debug("saved pickle")
    logging.debug(f"pickle_data: {pickle_data}")


@sentry_sdk.trace
def get_oura_client(oauth_code=None, force_reauth=False):
    return OuraClientV2(personal_access_token=OURA_TOKEN)

@sentry_sdk.trace
def get_oura_client_oauth(oauth_code=None, force_reauth=False):
    logging.debug("assembling oura client")
    pickle_data = setup_pickle()
    logging.debug("loaded/initialized pickle")
    logging.debug(f"pickle_data: {pickle_data}")
    logging.debug(f"repr(oauth_code): {repr(oauth_code)}")

    if 'access_token' not in pickle_data or 'refresh_token' not in pickle_data or \
       oauth_code is not None or force_reauth:

        auth_client = OuraOAuth2Client(client_id=OURA_CLIENT_ID, client_secret=OURA_CLIENT_SECRET)
        # default scope is all
        authorize_url = auth_client.authorize_endpoint(redirect_uri='ouraring.ernie.org',scope=None)
        print("authorize_url: {authorize_url}".format(authorize_url=authorize_url))
        # https://cloud.ouraring.com/oauth/cool.dude?code=xxx&scope=email%20personal%20daily%20heartrate%20workout%20tag%20session&state=xxx
        if oauth_code is None:
            code = input("Enter code from redirect: ")
        else:
            code = oauth_code

        token_dict = auth_client.fetch_access_token(code=code)
        handle_auth_callback(token_dict)
        access_token = token_dict['access_token']
        refresh_token = token_dict['refresh_token']
    else:
        access_token = pickle_data['access_token']
        refresh_token = pickle_data['refresh_token']


    ouraclient = OuraClientV2(OURA_CLIENT_ID, OURA_CLIENT_SECRET, access_token, refresh_token, handle_auth_callback)
    return ouraclient


@sentry_sdk.trace
def main():
    """
    Read arguments, do auth, dl from oura, save to db
    """

    args = get_args()

    if args.debug:
        logging.getLogger().setLevel(getattr(logging, "DEBUG"))

    logging.debug("parsing dates")

    if args.date is None:
        end_date = datetime.datetime.now()
    else:
        #end_date = dateutil.parser.parse(args.date)
        end_date = args.date
    start_date = end_date - datetime.timedelta(days = args.days_back)

    # end date is exclusive
    end_date = end_date + datetime.timedelta(days = 1)
    logging.debug(f"start_date: {start_date}")
    logging.debug(f"end_date: {end_date}")

    ouraclient = get_oura_client( oauth_code=args.oauth_code, force_reauth=args.force_reauth)

    # wants strs
    # data = ouraclient.activity_summary(start = start_date, end = end_date)
    data = ouraclient.daily_activity(start_date = start_date.strftime("%Y-%m-%d"), end_date = end_date.strftime("%Y-%m-%d"))
    #get_daily_activity(start_date = start_date, end_date = end_date)
    #pprint.pprint(data)
    inserted_count = 0
    modified_count = 0
    processed_count = 0
    for activity in data['data']:
        activity['timestamp'] = dateutil.parser.parse(activity['timestamp']).astimezone(tz=pytz.utc).replace(tzinfo=None)
        activity['met']['timestamp'] = dateutil.parser.parse(activity['met']['timestamp']).astimezone(tz=pytz.utc).replace(tzinfo=None)
        result = store_activity(activity)
        wrote_to_db = False
        if result['matched_count'] == 0:
            inserted_count += 1
            wrote_to_db = True
        processed_count += 1
        if result['modified_count'] != 0:
            #print("Modified activity")
            wrote_to_db = True
        modified_count += result['modified_count']
        if wrote_to_db:
           dateonly = activity['timestamp'].date()
           PROCESSED_DATES[dateonly] = True
    if args.verbose or args.debug:
        print(f"Processed activities: {processed_count}")
        print(f"New activities: {inserted_count}")
        print(f"Modified activities: {modified_count}")
    for processed_date in PROCESSED_DATES:
        print(f"date: {processed_date}")



# return result from replace_one()
@sentry_sdk.trace
def store_activity(activity):
    activity_query = {"day": activity['day']}
    collection = get_collection()
    logging.debug(f"activity_query: {activity_query}")
    db_activity = collection.find_one(activity_query)
    #logging.debug(f"db_activity: {db_activity: .60}")

    do_replace = True
    if db_activity is not None:
        do_replace = False
        activity["_id"] = db_activity["_id"]
        for field in db_activity:
            if activity[field] != db_activity[field]:
                do_replace = True
                logging.debug(f"field diff: {field}")
                break
        logging.debug(f"here 0.5")
        if 'met' in activity:
            logging.debug(f"here 1")
            if 'met' not in db_activity:
                logging.debug(f"here 2")
                do_replace = True
            else:  # met in both
                logging.debug(f"here 3")
                if 'items' in activity['met']:
                    logging.debug(f"here 4")
                    if 'items' not in db_activity['met']:
                        logging.debug(f"here 5")
                        do_replace = True
                    else:  # items in both
                        logging.debug(f"here 6")
                        if activity['met']['items'] != db_activity['met']['items']:
                            logging.debug(f"here 7")
                            do_replace = True
            logging.debug(f"here 8")
        logging.debug(f"here 9")


    logging.debug(f"db_activity: {db_activity}")
    logging.debug(f"activity: {activity}")

    if do_replace:
        result = collection.replace_one(
            activity_query, activity, upsert=True)
        result_info = { "upserted_id": result.upserted_id, "modified_count": result.modified_count, "matched_count": result.matched_count }
    else:
        result_info = { "upserted_id": None, "modified_count": 0, "matched_count": 1 }
    logging.debug("result_info['upserted_id']: %s", result_info['upserted_id'])
    logging.debug("result_info['modified_count']: %s", result_info['modified_count'])
    return result_info


@sentry_sdk.trace
def get_collection():
    mongoclient = MongoClient(DB_URL)

    database = mongoclient[DB_NAME]

    return database[COLLECTION_NAME]

if __name__ == '__main__':
    try:
        with sentry_sdk.start_transaction(op="task", name=os.path.basename(sys.argv[0])):
            main()
    finally:
        sentry_sdk.flush()
