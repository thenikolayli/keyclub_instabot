# Keyclub Instabot

## Files:
- `key.json` - Google Service Account credentials file
- `current_events.json` - List of events that are currently posted (to prevent duplicates)
- `.env` - Environment variables
- `actions.log` - Log of actions this bot has performed

## Workflow:

1. Every day at 3:00 PM the bot will fetch all events in the next 7 days from the Google Calendar.
2. It will then save the sign up sheet docs and go to each one and check how many volunteers have signed up.
3. It will calculate how full the event is via volunteers_signed_up/total_spots and determine the priority.

- <=25% full = high priority
- <=50% full = medium priority
- <=75% full = low priority,
- anything above 75% doesn't count

4. It will then check that the event hasn't been uploaded yet and isn't in `event_log.json`, based on its name.
5. If not, it will generate the photo, upload it to imgbb, then to instagram, and save the name to `event_log.json`.
6. Every day at 2:00 PM, the bot checks `event_log.json` for all events and checks if their dates have passed,
if so, it removes that entry from the log.
