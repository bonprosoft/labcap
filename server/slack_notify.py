# -*- coding: utf-8 -*-

import json
import requests
import datetime

url = "https://hooks.slack.com/services/"
USERNAME = "yurei"
CHANNEL = "#room"

def create_timespan_string(timespan):
    return "%d日%d時間" % (timespan.days, timespan.seconds / (60 * 60))

def notify_active(username, timespan):
    item = {"text": "%sさんが入室しました。(前回の退室から %s ぶり)" % (str(username), create_timespan_string(timespan)), "username": USERNAME, "icon_emoji": ":ghost:", "channel": CHANNEL }
    try:
        r = requests.post(url, data = json.dumps(item))
    except Exception as e:
        pass

def notify_deactive(username, timespan):
    item = {"text": "%sさんが退室しました。(今回の滞在時間: %s)" % (str(username), create_timespan_string(timespan)), "username": USERNAME, "icon_emoji": ":ghost:", "channel": CHANNEL }
    try:
        r = requests.post(url, data = json.dumps(item))
    except Exception as e:
        pass

