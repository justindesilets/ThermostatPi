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
import glob

os.system('modprobe w1-gpio')
os.system('modprobe w1-therm')

base_dir = '/sys/bus/w1/devices/'
device_folder = glob.glob(base_dir + '28*')[0]
device_file = device_folder + '/w1_slave'

current_temp = 72
temp_f = 0
temp_c = 0
set_temp = 70

app = Flask(__name__)

@app.route("/")
def main_page():

	templateData = {
		'temp_f' : temp_f,
		'set_temp' : set_temp,
	}
	return render_template('main.html', **templateData)
@app.route("/override")
def override():
	return render_template('override.html')

@app.route("/heat_schedule", methods=['POST','GET'])
def heat_schedule():
	return render_template('heat_schedule.html')

@app.route("/cool_schedule", methods=['POST','GET'])
def cool_schedule():
	return render_template('cool_schedule.html')

def read_temp_raw():
	f = open(device_file, 'r')
	lines = f.readlines()
	f.close()
	return lines

def read_temp():
	global temp_c
	global temp_f
	while True:
		time.sleep(2)
	lines = read_temp_raw()
	while lines[0].strip()[-3:] != 'YES':
		time.sleep(0.2)
		lines = read_temp_raw()
	equals_pos = lines[1][equals_pos+2:]
	if equals_pos != -1:
		temp_string = lines[1][equals_pos+2:]
		temp_c = float(temp_string) / 1000.0
		temp_f = temp_c * 9.0 / 5.0 + 32.0





if __name__ == "__main__":
	app.run(host='0.0.0.0', port=80, debug=True,)
