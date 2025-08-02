from utils import fill_template, post_to_instagram, get_events, update_current_events, add_to_current_events, TZFormatter

from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials

import cloudinary
from cloudinary import uploader as cloudinary_uploader

from os import getenv
from dotenv import load_dotenv
from apscheduler.schedulers.blocking import BlockingScheduler
from zoneinfo import ZoneInfo
import json, logging


load_dotenv()

google_scopes = json.loads(getenv("GOOGLE_SCOPES"))
credentials = Credentials.from_service_account_file("key.json")

docs_service = build("docs", "v1", credentials=credentials)

calendar_service = build("calendar", "v3", credentials=credentials)
calendar_id = getenv("CALENDAR_ID")

fb_token = getenv("FB_TOKEN")

cloudinary.config(
    cloud_name=getenv("CLOUD_NAME"),
    api_key=getenv("CLOUD_API_KEY"),
    api_secret=getenv("CLOUD_API_SECRET"),
    secure=True
)

handler = logging.FileHandler(filename="actions.log", mode="a") # append new messages
formatter = TZFormatter(fmt='[%(asctime)s] [%(levelname)s] %(name)s: %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S',
                        tz=ZoneInfo("America/Los_Angeles"))
handler.setFormatter(formatter)

logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(handler)


# main function that runs every day at 3:00
def main():
    logging.info("Ran main loop")
    update_current_events()

    # gets list of events that should be posted
    events = get_events(calendar_service=calendar_service, docs_service=docs_service, calendar_id=calendar_id)

    for event in events:
        # creates output.jpg
        image = fill_template(
            post_type="Volunteers Needed",
            title=event.get("event_title"),
            description=event.get("event_description"),
            start_time=event.get("event_start"),
            end_time=event.get("event_end"),
            date=event.get("event_date"),
            address=event.get("event_address"),
            priority=event.get("event_priority"),
        )
        image.save("output.jpg")

        # uploads to cloudinary, gets asset id (for removal) and secure url (HTTPS url for posting)
        upload_result = cloudinary_uploader.upload(file="output.jpg", return_delete_token=True)
        public_id, secure_url = upload_result.get("public_id"), upload_result.get("secure_url")
        # posts to instagram
        post_to_instagram(
            caption=f"{event.get('event_title')}\n\n{event.get('event_description')}\n\n{event.get('event_url')}",
            image_url=secure_url,
            fb_token=fb_token,
        )
        # adds to log
        add_to_current_events(event_title=event.get("event_title"), event_date=event.get("event_date"), public_id=public_id)
        print(f"Successfully uploaded {event.get('event_title')}")
        logging.info(f"Successfully posted {event.get('event_title')}")

# runs main every day at 3:00 PM
scheduler = BlockingScheduler(timezone=ZoneInfo("America/Los_Angeles"))
scheduler.add_job(main, "cron", hour=15)
scheduler.start()