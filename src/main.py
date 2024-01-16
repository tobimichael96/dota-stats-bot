from datetime import datetime, timedelta
import os
import logging
import json

import requests
from flask import Flask, redirect

import urllib.parse

app = Flask(__name__)
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

LAST_CHECK = (datetime.now() - timedelta(hours=12))

if "PLAYER_ID" in os.environ:
    PLAYER_ID = os.environ['PLAYER_ID']
if "BOT_TOKEN" in os.environ:
    BOT_TOKEN = os.environ['BOT_TOKEN']
if "GROUP_ID" in os.environ:
    GROUP_ID = os.environ['GROUP_ID']


def get_latest_match():
    request_return = requests.get(f"https://api.opendota.com/api/players/{PLAYER_ID}/recentMatches")
    request_content = json.loads(request_return.content)
    logging.debug(request_content)
    if request_return.status_code == 200 and len(request_content) > 0:
        return datetime.fromtimestamp(request_content[0]["start_time"])
    else:
        logging.error(f"API data was not right: {request_content}")
        return None


def get_player_name():
    request_return = requests.get(f"https://api.opendota.com/api/players/{PLAYER_ID}")
    request_content = json.loads(request_return.content)["profile"]["personaname"]
    if request_return.status_code == 200:
        return request_content
    else:
        logging.error(f"API data was not right: {request_content}")
        return None


@app.route('/')
def home():
    return redirect("https://www.tobiasmichael.de/", code=302)


@app.route('/daily')
def daily():
    global LAST_CHECK
    if (datetime.now() - LAST_CHECK) > timedelta(hours=12):
        LAST_CHECK = datetime.now()
        player_name = get_player_name()
        latest_match = get_latest_match()
        if latest_match is None or player_name is None:
            return {'Response': 'Error'}, 400
        message_text = f"{player_name} played their last match at {latest_match.strftime('%d.%m.%Y')}."
        logging.debug(message_text)
        return send_message(message_text, True)
    else:
        logging.warning(f'Last check was only {(datetime.now() - LAST_CHECK).seconds / 60 / 60} hours ago.')
        return {'Response': 'Limit reached'}, 429


@app.route('/cron')
def cron():
    player_name = get_player_name()
    latest_match = get_latest_match()
    if latest_match is None or player_name is None:
        return {'Response': 'Error'}, 400
    if latest_match.strftime('%Y') == "2024":
        message_text = f"{player_name} just started a game at {latest_match.strftime('%d.%m.%Y')}."
        logging.debug(message_text)
        return send_message(message_text)
    else:
        logging.error("Run did not produce anything.")
        return {'Response': 'Done'}, 204


def send_message(message_text, message_silent=False):
    full_message_url = f'https://api.telegram.org/bot{os.environ["BOT_TOKEN"]}/sendMessage?' \
                       + urllib.parse.urlencode({
        "chat_id": os.environ["GROUP_ID"],
        "text": message_text.replace('-', '\\-').replace('.', '\\.'),
        "parse_mode": "MarkdownV2",
        "disable_notification": message_silent
    })
    logging.info(f"See full message here: {full_message_url}")
    bot_request = requests.get(full_message_url)
    if bot_request.status_code == 200:
        logging.info('Send message successful.')
        return {'Response': 'Done'}, 200
    else:
        logging.error(f"Sending message failed: {bot_request.content}")
        return {'Response': 'Error'}, 400


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
