# -*- coding: utf-8 -*-

from pymongo import MongoClient
import datetime
from flask import Flask, request, render_template, redirect, url_for, abort
import json
import logging
import time
from subprocess import Popen, PIPE
import re
import slack_notify
import threading

startTime = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
logging.basicConfig(filename='logs/activity_' + startTime + '.log', filemode='w', format='%(asctime)s %(message)s', level=logging.INFO)

con = MongoClient("localhost")
db = con["labcap"]

DATETIME_FORMAT = "%Y%m%d%H%M%S"
ACTIVE_THRESHOLD_SEC = 60 * 15

app = Flask(__name__)

class DeactiveWatcher(threading.Thread):
    def __init__(self, t):
        super(DeactiveWatcher, self).__init__()
        self.t = t

    def run(self):
        while True:
            for user in db.user.find({"is_active": True}):
                if (not is_active(user["last_active"])):
                    slack_notify.notify_deactive(user["username"], datetime.datetime.strptime(user["last_active"], DATETIME_FORMAT) - datetime.datetime.strptime(user["since_active"], DATETIME_FORMAT))
                    logging.info("Event: Deactive, UserName: %s, Time: %s" % (user["username"], user["last_active"]))
                    user["is_active"] = False
                    db.user.save(user)
            time.sleep(self.t)

def arp_ip(ip):
    Popen(["ping", "-c 1", ip], stdout = PIPE)
    pid = Popen(["arp", "-n", ip], stdout=PIPE)
    s = pid.communicate()[0]
    group = re.search(r"(([a-f\d]{1,2}\:){5}[a-f\d]{1,2})", s)
    if (not group):
        return None

    mac = group.groups()[0]
    return mac

def is_active(last_active):
    last_active_datetime = datetime.datetime.strptime(last_active, DATETIME_FORMAT)
    diff = datetime.datetime.now() - last_active_datetime
    if (diff.seconds > ACTIVE_THRESHOLD_SEC):
        return False

    return True

@app.route("/")
def register():
    return render_template("top.html")

@app.route("/register", methods=["POST"])
def register_name():
    args = request.form
    if (not "username" in args):
        return redirect(url_for('register'))

    username = args["username"].strip()
    if (username == ""):
        return redirect(url_for('register'))

    remote_ip = request.remote_addr
    mac_addr = arp_ip(remote_ip)

    if (not mac_addr):
        return render_template("error.html", error="Can't resolve MAC Address of IP: %s" % str(remote_ip))

    user = db.user.find_one({"username": username})
    if (not user):
        user = {"username": username, "since_active": datetime.datetime.now().strftime(DATETIME_FORMAT), "is_active": False, "last_active": datetime.datetime.now().strftime(DATETIME_FORMAT), "address": [ mac_addr ]}
        db.user.insert(user)
    else:
        if (not mac_addr in user["address"]):
            user["address"].append(mac_addr)
            db.user.save(user)

    return render_template("register.html", username = username, mac_addr = mac_addr, ip_addr = remote_ip)

@app.route("/api/list.json")
def list_user():
    temp = []
    for user in db.user.find():
        temp.append(user["username"])
    return json.dumps(temp)

@app.route("/api/details/<name>.json")
def detail_user(name):
    user = db.user.find_one({"username": name})
    if (not user):
        abort(404)
    else:
        temp = {"username": name, "address": user["address"], "last_active": user["last_active"], "since_active": user["since_active"], "is_active": is_active(user["last_active"])}
        return json.dumps(temp)

@app.route("/api/is_active/<name>.json")
def is_active_user(name):
    user = db.user.find_one({"username": name})
    if (not user):
        abort(404)
    else:
        temp = {"is_active": is_active(user["last_active"])}
        return json.dumps(temp)

@app.route("/api/record/<mac_addr>")
def record_active(mac_addr):
    user = db.user.find_one({"address": {"$in":[mac_addr] }})
    if (not user):
        return "OK"
    else:
        last_active = datetime.datetime.strptime(user["last_active"], DATETIME_FORMAT)
        if (not user["is_active"]):
            user["since_active"] = datetime.datetime.now().strftime(DATETIME_FORMAT)
            # 通知
            slack_notify.notify_active(user["username"], datetime.datetime.now() - last_active)
            logging.info("Event: Active, UserName: %s, Time: %s" % (user["username"], user["since_active"]))

        user["last_active"] = datetime.datetime.now().strftime(DATETIME_FORMAT)
        user["is_active"] = True
        db.user.save(user)
        return "OK"

if __name__ == "__main__":
    watcher = DeactiveWatcher(1 * 60)
    watcher.start()
    log = logging.getLogger('werkzeug')
    # app.logger.setLevel(logging.WARNING)
    log.setLevel(logging.ERROR)
    app.run(host="0.0.0.0", port=5050)

