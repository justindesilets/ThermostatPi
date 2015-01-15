#!/usr/bin/python
from flask import Flask, render_template, request, Response
from functools import wraps
import datetime
import time
import sys
import thread
import feedparser
import os
import urllib2
import json


f = urllib2.urlopen('http://api.wunderground.com/api/a21833d6474a6f82/geolookup/conditions/q/UT/Riverton.json') 
json_string = f.read() 
parsed_json = json.loads(json_string) 
location = parsed_json['location']['city'] 
temp_f = parsed_json['current_observation']['temp_f'] 
f.close()

current_temp = 72
wu_api_key = 'a21833d6474a6f82'
wu_state = 'UT'
wu_city = 'Riverton'

app = Flask(__name__)

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


