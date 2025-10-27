#!/usr/bin/env python3
"""
Download Oura activity data and save in database
"""

import argparse
import sys
import dateutil
import logging
import os
from pymongo import MongoClient
from oura.v2 import OuraClientV2
import pytz
import datetime


import sentry_sdk
from sentry_sdk.integrations.pymongo import PyMongoIntegration

sentry_sdk.init(
    debug=False,
)


def sentry_init(debug=False):
    sentry_sdk.init(
        traces_sample_rate=1.0,
        profiles_sample_rate=1.0,
        enable_tracing=True,
        integrations=[
            PyMongoIntegration(),
        ],
        # debug=debug,
        debug=False,
    )


autoupdate_version = 278

DB_URL = os.environ["OURA_MONGODB_URI"]

DB_NAME = "oura"
COLLECTION_NAME = "activity"

OURA_TOKEN = os.environ["OURA_TOKEN"]

# ACTIVITY_VERSION = 0.1
# ACTIVITY_VERSION = 0.2  # change timestamps to date objects
# ACTIVITY_VERSION = 0.3  # Add map
# output "day" field string instead of converted timestamp (let app and service deal more with timestamps)
ACTIVITY_VERSION = 0.4


@sentry_sdk.trace
def get_args():
    """Parse command line args"""
    parser = argparse.ArgumentParser(description="Store Oura activity data in db")
    parser.add_argument(
        "--days_back",
        required=False,
        default=3,
        help="Number of days back to search Oura",
        type=int,
    )
    parser.add_argument(
        "--date",
        required=False,
        default=None,
        help="Date to search",
        type=datetime.date.fromisoformat,
    )
    parser.add_argument(
        "--oauth_code",
        required=False,
        help="Code for oauth to skip initial auth request and prompt",
        type=str,
    )
    parser.add_argument(
        "--force_reauth", default=False, help="Re-auth to Oura", action="store_true"
    )
    parser.add_argument(
        "--verbose",
        default=False,
        help="Print (slight) verbose info to stdout",
        action="store_true",
    )
    parser.add_argument(
        "--debug",
        default=False,
        help="Print debugging info to stderr",
        action="store_true",
    )
    parser.add_argument(
        "--dry-run", default=False, help="Don't write to DB", action="store_true"
    )
    args = parser.parse_args()
    return args


@sentry_sdk.trace
def get_oura_client(oauth_code=None, force_reauth=False):
    return OuraClientV2(personal_access_token=OURA_TOKEN)


@sentry_sdk.trace
def main():
    """
    Read arguments, do auth, dl from oura, save to db
    """

    args = get_args()
    print(f"args.debug: {args.debug}")
    sentry_init(debug=args.debug)

    if args.debug:
        logging.getLogger().setLevel(getattr(logging, "DEBUG"))

    logging.debug("parsing dates")

    if args.date is None:
        end_date = datetime.datetime.now()
    else:
        end_date = args.date
    start_date = end_date - datetime.timedelta(days=args.days_back)

    # end date is exclusive
    end_date = end_date + datetime.timedelta(days=1)
    logging.debug(f"start_date: {start_date}")
    logging.debug(f"end_date: {end_date}")

    start_date_string = start_date.strftime("%Y-%m-%d")
    end_date_string = end_date.strftime("%Y-%m-%d")

    resp = run(
        start_date_string,
        end_date_string,
        oauth_code=args.oauth_code,
        force_reauth=args.force_reauth,
        dry_run=args.dry_run,
    )
    # processed_dates, processed_count, inserted_count, modified_count =

    if args.verbose or args.debug:
        print(f"Processed activities: {resp['processed_count']}")
        print(f"New activities: {resp['inserted_count']}")
        print(f"Modified activities: {resp['modified_count']}")
    for processed_date in resp["processed_dates"]:
        print(f"date: {processed_date}")


def run(
    start_date_string="",
    end_date_string="",
    oauth_code=None,
    force_reauth=False,
    dry_run=False,
):

    print("oura_to_db.run()")

    processed_dates = dict()
    print(f"start_date_string: {start_date_string}")
    print(f"end_date_string: {end_date_string}")

    ouraclient = get_oura_client(oauth_code=oauth_code, force_reauth=force_reauth)

    data = ouraclient.daily_activity(
        start_date=start_date_string, end_date=end_date_string
    )
    print(f"data: {data}")
    inserted_count = 0
    modified_count = 0
    processed_count = 0
    for activity in data["data"]:
        activity["activity_version"] = ACTIVITY_VERSION
        activity["timestamp"] = (
            dateutil.parser.parse(activity["timestamp"])
            .astimezone(tz=pytz.utc)
            .replace(tzinfo=None)
        )
        activity["met"]["timestamp"] = (
            dateutil.parser.parse(activity["met"]["timestamp"])
            .astimezone(tz=pytz.utc)
            .replace(tzinfo=None)
        )
        result = store_activity(activity=activity, dry_run=dry_run)
        wrote_to_db = False
        if result["matched_count"] == 0:
            inserted_count += 1
            wrote_to_db = True
        processed_count += 1
        if result["modified_count"] != 0:
            # print("Modified activity")
            wrote_to_db = True
        modified_count += result["modified_count"]
        if wrote_to_db:
            dateonly = activity["day"]
            processed_dates[dateonly] = True
        logging.debug(f"wrote_to_db: {wrote_to_db}")
    print(f"processed_dates.keys(): {processed_dates.keys()}")
    print(f"dir(processed_dates): {dir(processed_dates)}")
    return {
        "processed_dates": processed_dates,
        "processed_count": processed_count,
        "inserted_count": inserted_count,
        "modified_count": modified_count,
    }


# return result from replace_one()
@sentry_sdk.trace
def store_activity(activity=None, dry_run=False):
    activity_query = {"day": activity["day"]}
    collection = get_collection()
    logging.debug(f"activity_query: {activity_query}")
    db_activity = collection.find_one(activity_query)
    # logging.debug(f"db_activity: {db_activity: .60}")

    do_replace = True
    if db_activity is not None:
        do_replace = False
        activity["_id"] = db_activity["_id"]
        for field in db_activity:
            # if field != "update_timestamp" and field not in db_activity or activity[field] != db_activity[field]:
            if field != "update_timestamp" and activity[field] != db_activity[field]:
                do_replace = True
                logging.debug(f"field diff: {field}")
                break
        logging.debug("here 0.5")
        if "activity_version" not in db_activity:
            do_replace = True
        elif "met" in activity:
            logging.debug("here 1")
            if "met" not in db_activity:
                logging.debug("here 2")
                do_replace = True
            else:  # met in both
                logging.debug("here 3")
                if "items" in activity["met"]:
                    logging.debug("here 4")
                    if "items" not in db_activity["met"]:
                        logging.debug("here 5")
                        do_replace = True
                    else:  # items in both
                        logging.debug("here 6")
                        if activity["met"]["items"] != db_activity["met"]["items"]:
                            logging.debug("here 7")
                            do_replace = True
            logging.debug("here 8")
        logging.debug("here 9")

    logging.debug(f"db_activity: {db_activity}")
    activity["update_timestamp"] = datetime.datetime.now()
    logging.debug(f"activity: {activity}")

    if do_replace:
        if dry_run:
            logging.debug("Skipping db call in dry run mode")
            result_info = {
                "upserted_id": None,
                "modified_count": 1,
                "matched_count": 1,
            }
        else:
            result = collection.replace_one(activity_query, activity, upsert=True)
            result_info = {
                "upserted_id": result.upserted_id,
                "modified_count": result.modified_count,
                "matched_count": result.matched_count,
            }
    else:
        result_info = {"upserted_id": None, "modified_count": 0, "matched_count": 1}
    logging.debug("result_info['upserted_id']: %s", result_info["upserted_id"])
    logging.debug("result_info['modified_count']: %s", result_info["modified_count"])
    return result_info


@sentry_sdk.trace
def get_collection():
    mongoclient = MongoClient(DB_URL)

    database = mongoclient[DB_NAME]

    return database[COLLECTION_NAME]


@sentry_sdk.trace
def mongodb_ping():
    return MongoClient(DB_URL)[DB_NAME].command("ping")


@sentry_sdk.trace
def oura_ping():
    ouraclient = get_oura_client()
    if "email" in ouraclient.personal_info():
        return {"ok": True}


if __name__ == "__main__":
    try:
        with sentry_sdk.start_transaction(
            op="task", name=os.path.basename(sys.argv[0])
        ):
            main()
    finally:
        sentry_sdk.flush()
