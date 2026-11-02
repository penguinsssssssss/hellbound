"""Hellbound: a Slack bot that screams about going to hell.

Posts one message from MESSAGES to a channel every --every minutes, give or take
--jitter, cycling through the whole list in a shuffled order before repeating.
Standard library only. Run:

    python3 hellbound.py                      # token and channel from env or .env
    python3 hellbound.py --every 30 --jitter 10
    python3 hellbound.py --once               # scream once, then exit
    python3 hellbound.py --dry-run --every 0.05 --jitter 0   # print, don't post
"""

import argparse
import json
import logging
import os
import random
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

log = logging.getLogger("hellbound")

POST_URL = "https://slack.com/api/chat.postMessage"

# Slack errors no amount of waiting will fix; anything else is retried next tick.
FATAL_ERRORS = {"invalid_auth", "not_authed", "account_inactive", "token_revoked",
                "channel_not_found", "not_in_channel", "is_archived", "missing_scope"}

# {time} and {day} are filled in when the message is sent.
MESSAGES = [
    "I'M GOING TO HELL!!!!!!",
    "AAAAAAAAAAAAAAAAAAAAAAAAAAA HELL AAAAAAAAAAAAAAAAAAAAAAAAAA :fire:",
    "IT'S {time} AND I'M STILL GOING TO HELL",
    "STATUS UPDATE: STILL GOING TO HELL. ETA UNKNOWN. :fire:",
    "THE FLOOR IS GETTING WARMER. I'M GOING TO HELL.",
    "SOMEBODY TELL MY MOTHER I'M GOING TO HELL",
    "I CHECKED THE LIST. MY NAME IS ON IT. I'M GOING TO HELL!!!",
    "I SAW MY NAME CARVED INTO THE GATES OF HELL. THEY EVEN SPELLED IT RIGHT. "
    "THAT'S HOW I KNOW IT'S REAL.",
    "ONE-WAY TICKET. NO REFUNDS. HELL. :fire::fire::fire:",
    "I CAN SMELL THE SULFUR FROM HERE",
    "I'VE BEEN ASSIGNED A SEAT IN HELL. IT'S THE MIDDLE SEAT.",
    "I'M GOING TO HELL AND I DIDN'T EVEN GET A WINDOW SEAT",
    "HELL HAS A SLACK WORKSPACE AND THEY JUST SENT ME AN INVITE",
    "THE DEVIL LEFT ME ON READ. I'M GOING TO HELL ANYWAY.",
    "I MICROWAVED FISH IN THE OFFICE KITCHEN. I'M GOING TO HELL.",
    "I SAID \"PER MY LAST EMAIL.\" I'M GOING TO HELL.",
    "I LEFT A SHOPPING CART IN THE MIDDLE OF THE PARKING LOT. STRAIGHT TO HELL.",
    "I USED THE LAST OF THE COFFEE AND DIDN'T MAKE MORE. I'M GOING TO HELL.",
    "I SKIPPED THE TERMS AND CONDITIONS. ALL OF THEM. EVER. HELL. HELL. HELL.",
    "WHAT'S THE WI-FI PASSWORD IN HELL. ASKING FOR ME. BECAUSE I'M GOING THERE.",
    "SET A REMINDER: GO TO HELL. OH WAIT. IT'S AUTOMATIC.",
    "COUNTDOWN TO HELL: T-MINUS WHENEVER. :fire:",
    "HAPPY {day}. I'M GOING TO HELL.",
    "I REPLIED \"SOUNDS GOOD\" WITHOUT READING IT. I'M GOING TO HELL.",
    "PLEASE DON'T REACT WITH :fire:. IT'S TOO SOON. I'M GOING TO HELL.",
    "NOBODY ASKED BUT I'M GOING TO HELL",
    "HELL? I'M GOING THERE. HELL!!!!!!!!!!!!!!!!",
]


def load_dotenv(path=Path(__file__).with_name(".env")):
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip().strip("'\""))


def screams():
    """Yield messages forever, each one once per shuffled pass, never twice in a row."""
    last = None
    while True:
        bag = random.sample(MESSAGES, len(MESSAGES))
        if bag[0] == last:
            bag.append(bag.pop(0))
        for template in bag:
            now = datetime.now()
            hour = now.hour % 12 or 12
            yield template.format(time=f"{hour}:{now:%M} {now:%p}",
                                  day=now.strftime("%A").upper())
        last = bag[-1]


class FatalSlackError(Exception):
    pass


def post(token, channel, text):
    body = json.dumps({"channel": channel, "text": text}).encode()
    req = urllib.request.Request(POST_URL, data=body, headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=utf-8",
    })
    for _ in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.load(resp)
        except urllib.error.HTTPError as e:
            if e.code != 429:
                raise
            wait = int(e.headers.get("Retry-After", 30))
            log.warning("rate limited, retrying in %ds", wait)
            time.sleep(wait)
            continue
        if result.get("ok"):
            return
        error = result.get("error", "unknown_error")
        if error in FATAL_ERRORS:
            raise FatalSlackError(error)
        raise RuntimeError(error)
    raise RuntimeError("still rate limited after 3 tries")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--channel", help="channel ID or #name (default: $SLACK_CHANNEL)")
    parser.add_argument("--every", type=float, default=60,
                        help="minutes between screams (default 60)")
    parser.add_argument("--jitter", type=float, default=15,
                        help="+/- random minutes added to each wait (default 15)")
    parser.add_argument("--once", action="store_true", help="scream once and exit")
    parser.add_argument("--dry-run", action="store_true",
                        help="print screams instead of posting; needs no token")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    load_dotenv()
    token = os.environ.get("SLACK_BOT_TOKEN")
    channel = args.channel or os.environ.get("SLACK_CHANNEL")
    if not args.dry_run and not (token and channel):
        raise SystemExit("set SLACK_BOT_TOKEN and SLACK_CHANNEL (in the environment or .env)")

    for text in screams():
        if args.dry_run:
            log.info("would post: %s", text)
        else:
            try:
                post(token, channel, text)
                log.info("posted: %s", text)
            except FatalSlackError as e:
                raise SystemExit(f"Slack refused: {e} (check the token, scopes, and channel)")
            except (OSError, RuntimeError) as e:
                log.error("post failed, will try again next time: %s", e)
        if args.once:
            return
        wait = max(args.every + random.uniform(-args.jitter, args.jitter), 0.01)
        log.info("next scream in %.1f min", wait)
        time.sleep(wait * 60)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
