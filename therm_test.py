#!/usr/bin/python
from flask import Flask, render_template, request, Response
from functools import wraps
from apscheduler.schedulers.blocking import BlockingScheduler
import datetime
import time
import sys
import thread
import feedparser
import os
import urllib2
import json

wu_url = 'http://api.wunderground.com/api/'
wu_loc = '/geolookup/conditions/q/'
current_temp = 72
wu_api_key = 'a21833d6474a6f82'
wu_state = 'UT'
wu_city = 'Riverton'
queryURL = wu_url + wu_api_key + wu_loc + wu_state + '/' + wu_city + '.json'
location = 'city'
temp_f = 0

def wu_update():
	with app.app_context():
		global location
		global temp_f
		f = urllib2.urlopen(queryURL)
		json_string = f.read()
		parsed_json = json.loads(json_string)
		location = parsed_json['location']['city']
		temp_f = parsed_json['current_observation']['temp_f']
		f.close()

app = Flask(__name__)

@app.before_first_request
def initialize():
	apsched = BlockingScheduler()
	apsched.add_job(wu_update, 'interval',  minutes=1)
	apsched.start()

@app.route("/")
def main_page():

	templateData = {
		'current_temperature' : current_temp,
		'current_location' : location,
		'outside_temp' : temp_f
	}
	return render_template('main.html', **templateData)
@app.route("/override")
def override():
	return render_template('override.html')

@app.route("/schedule")
def schedule():
	return render_template('schedule.html')

if __name__ == "__main__":
	app.run(host='0.0.0.0', port=80, debug=True)
