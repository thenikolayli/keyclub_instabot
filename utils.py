# utility functions for main.py
from PIL import Image, ImageFont
from pilmoji import Pilmoji
from zoneinfo import ZoneInfo
from datetime import datetime, timedelta
from cloudinary import uploader as cloudinary_uploader
import requests, json, logging, re

template = "instabot_template.jpg"
font_path = "centurygothic.ttf"

middle = 1080 // 2
left = 120
width = 1080 - (left * 2)

post_type_y_start = 100
post_type_y_end = 220
title_y_start = post_type_y_end
title_y_end = 400
description_y_start = title_y_end + 30
description_y_end = 900
info_y_start = description_y_end
info_y_end = 1100


# ------------------- Utility Functions -------------------

# breaks text into lines to fit max_width
def break_text(text, font, max_width):
    words = text.split()
    lines = []
    line = ""
    broken_text = ""

    for index in range(len(words)):
        word = words[index]
        # if line isn't blank, add on to it, otherwise start it with the current word
        if line:
            temp_line = line + " " + word
        else:
            temp_line = word

        # check if the line fits within the width
        temp_bbox = font.getbbox(temp_line)
        temp_line_width = temp_bbox[2] - temp_bbox[0]
        # if new line is too wide or has a special emoji, start a new line, otherwise continue
        if temp_line_width > max_width or words[index] in ["📅", "⌚", "📍"]:
            lines.append(line)
            line = word
        else:
            line = temp_line
    # appends last line if there is one
    lines.append(line)

    for line in lines:
        broken_text += line + "\n"

    return broken_text

# fits text into max_width and max_height to have biggest font size, returns text string and font size
def fit_text(text, max_width, max_height, size = 2, max_size = 100):
    global font_path
    font = ImageFont.truetype(font_path, size)
    temp_text = break_text(text, font, max_width)
    ascend, descent = font.getmetrics()
    temp_text_line_height = ascend + descent
    temp_text_height = temp_text_line_height * temp_text.count("\n")

    # if the text is too tall or the size is beyond the limit, decrement it and return, otherwise increment and rerun
    if temp_text_height > max_height or size > max_size:
        size -= 2
        font = ImageFont.truetype(font_path, size)
        return break_text(text, font, max_width), size
    else:
        return fit_text(text, max_width, max_height, size + 2, max_size)

# returns the fullness of an event, volunteers_signed_up/total_spots
def get_event_fullness(docs_url, docs_service_param):
    docs_url = docs_url.split("id=")[1]
    document = docs_service_param.documents().get(documentId=docs_url).execute()
    body_content = document.get("body").get("content")
    tables = []
    rows = []
    volunteers = 0
    empty = 0

    # gets all tables from sign up doc
    for item in body_content:
        if "table" in item:
            table = item.get("table")
            tables.append(table)

    # removes the first table because its just event info
    tables.pop(0)

    # gets rows from each table and appends them
    for table in tables:
        for row in table.get("tableRows"):
            rows.append(row)
        rows.append(table.get("tableRows"))

    # removes the first row because its the header row
    rows.pop(0)

    # checks if the first cell of each row is \n, if yes then its empty, otherwise theres a volunteer
    for row in rows:
        try:
            content = row.get("tableCells")[1].get("content")[0].get("paragraph").get("elements")[0].get("textRun").get("content")

            if content == "\n":
                empty += 1
            else:
                volunteers += 1
        except AttributeError: pass

    return volunteers / (volunteers + empty)

# returns whether or not an event has been posted before
def in_current_events(event_title):
    with open("current_events.json", "r") as file:
        current_events = json.load(file)
    for event in current_events:
        if event.get("event_title") == event_title:
            return True
    return False

# formats datetime to remove the seconds column and adds the period
def format_time(datetime_param):
    datetime_param = datetime.fromisoformat(datetime_param).time()
    period = datetime_param.strftime("%p")

    # converts it to 12 hour time
    hour, minute = datetime_param.hour, datetime_param.minute
    if hour > 12:
        hour -= 12
    hour = str(hour)
    # if the minute is single digit
    if minute < 10:
        minute = "0" + str(minute)
    minute = str(minute)
    datetime_param = f"{hour}:{minute} {period}"

    return datetime_param


# ------------------- Main Functions -------------------

# updates the log and removes passed events
def update_current_events():
    today = datetime.today()
    new_current_events = []

    with open("current_events.json", "r") as file:
        current_events = json.load(file)

    # check if each event passed
    for event in current_events:
        # if yes, delete it. otherwise add it to the new_log
        if datetime.strptime(event.get("event_date"), "%Y/%m/%d") < today:
            cloudinary_uploader.destroy(event.get("public_id"))
            logging.info(f"Removed {event.get('event_title')} from current events")
        else:
            new_current_events.append(event)

    with open("current_events.json", "w") as file:
        json.dump(new_current_events, file)

    logging.info("Updated current events")

# adds an event to the log
def add_to_current_events(event_title, event_date, public_id):
    with open("current_events.json", "r") as file:
        current_events = json.load(file)
    current_events.append({"event_title": event_title, "event_date": event_date, "public_id": public_id})
    with open("current_events.json", "w") as file:
        json.dump(current_events, file)
    logging.info(f"Added {event_title} to current events")

# generates a png with event info
def fill_template(post_type, title, description, start_time, end_time, date, address, priority = None):
    global template, font_path, middle, left, width, post_type_y_start, post_type_y_end, title_y_start, title_y_end, description_y_start, description_y_end, info_y_start, info_y_end
    image = Image.open(template).convert("RGB")
    # draw = ImageDraw.Draw(image)
    info = f"📅 {date} ⌚ From {start_time} to {end_time} 📍 {address}"
    if priority:
        post_type = f"{post_type}: {priority}"

    post_type, post_type_font_size = fit_text(post_type, width, post_type_y_end - post_type_y_start)
    post_type_font = ImageFont.truetype(font_path, post_type_font_size)
    title, title_font_size = fit_text(title, width, title_y_end - title_y_start)
    title_font = ImageFont.truetype(font_path, title_font_size)
    description_max_font_size = title_font_size if title_font_size - 15 <= 2 else title_font_size - 15
    description, description_font_size = fit_text(description, width, description_y_end - description_y_start, max_size=description_max_font_size)
    description_font = ImageFont.truetype(font_path, description_font_size)
    info, info_font_size = fit_text(info, width, title_y_end - title_y_start)
    info_font = ImageFont.truetype(font_path, info_font_size)

    with Pilmoji(image) as pilmoji:
        pilmoji.text((middle, post_type_y_start), post_type, font=post_type_font, fill="black", anchor="ma")
        pilmoji.text((middle, title_y_start), title, font=title_font, fill="black", anchor="ma")
        pilmoji.text((left, description_y_start), description, font=description_font, fill="black", anchor="la")
        pilmoji.text((left, info_y_start), info, font=info_font, fill="black", anchor="la")

    # lines for deciding starting and ending y positions
    # draw.rectangle((left, post_type_y_start, left + width, post_type_y_end), None, "red", width=1)
    # draw.rectangle((left, title_y_start, left + width, title_y_end), None, "blue", width=1)
    # draw.rectangle((left, description_y_start, left + width, description_y_end), None, "orange", width=1)
    # draw.rectangle((left, info_y_start, left + width, info_y_end), None, "black", width=1)

    return image

# creates a container and posts it to instagram
def post_to_instagram(caption, image_url, fb_token):
    response = requests.post(
        f"https://graph.instagram.com/v23.0/me/media",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {fb_token}",
        },
        data={
            "image_url": image_url,
            "caption": caption
        }
    )

    if response.status_code == 200:
        container_id = response.json()["id"]

        requests.post(
            f"https://graph.instagram.com/v23.0/me/media_publish",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {fb_token}",
            },
            data={
                "creation_id": container_id,
            }
        )
        return container_id

# returns a list of upcoming events that should be posted in the next 7 days
def get_events(calendar_service, docs_service, calendar_id):
    now = datetime.now(ZoneInfo("America/Los_Angeles")).isoformat()
    week = (datetime.now(ZoneInfo("America/Los_Angeles")) + timedelta(days=7)).isoformat()
    all_events = calendar_service.events().list(calendarId=calendar_id, timeMin=now, timeMax=week).execute()
    all_events = all_events.get("items", [])
    return_events = []

    for event in all_events:
        try:
            event_title = event.get("summary")
            event_description = event.get("description")
            clean = re.compile("<[^>]+>")
            event_description = re.sub(clean, "", event_description)

            event_url = event.get("attachments")[0].get("fileUrl")
            event_address = event.get("location")

            # skip if theres no start or end time
            if not event.get("start").get("dateTime"):
                logging.info(f"Skipped fetching {event_title}: no start/end time")
                continue
            event_start = format_time(event.get("start").get("dateTime"))
            event_end = format_time(event.get("end").get("dateTime"))
            event_year, event_month, event_day = str(datetime.fromisoformat(event.get("start").get("dateTime")).date()).split("-")
            event_date = f"{event_month}/{event_day}/{event_year}" # month day year!

            event_fullness = get_event_fullness(event_url, docs_service)
            event_priority = ""
            # if event is too full, is already in the log (has been posted)
            if event_fullness > .75 or in_current_events(event_title):
                logging.info(f"Skipped fetching {event_title}: too full or already in current events")
                continue
            elif event_fullness <= .25:
                event_priority = "High Priority!!!"
            elif event_fullness <= .5:
                event_priority = "Medium Priority!!"
            elif event_fullness <= .75:
                event_priority = "Low Priority!"

            return_events.append({
                "event_title": event_title,
                "event_description": event_description,
                "event_url": event_url,
                "event_address": event_address,
                "event_date": event_date,
                "event_start": event_start,
                "event_end": event_end,
                "event_priority": event_priority,
            })
            logging.info(f"Fetched {event_title} from get_events")
        except KeyError: pass
    logging.info(f"Fetched {len(return_events)} new events")
    return return_events

# formatter for python logging
class TZFormatter(logging.Formatter):
    def __init__(self, fmt=None, datefmt=None, tz=ZoneInfo("America/Los_Angeles")):
        super().__init__(fmt=fmt, datefmt=datefmt)
        self.tz = tz

    def formatTime(self, record, datefmt=None):
        dt = datetime.fromtimestamp(record.created, self.tz)
        if datefmt:
            return dt.strftime(datefmt)
        return dt.isoformat()