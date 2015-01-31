#!/usr/bin/python
from flask import Flask, render_template, request, Response
from functools import wraps
from apscheduler.schedulers.blocking import BlockingScheduler
from w1thermsensor import W1ThermSensor
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

"""base_dir = '/sys/bus/w1/devices/'
device_folder = glob.glob(base_dir + '28*')[0]
device_file = device_folder + '/w1_slave'"""

sensor = W1ThermSensor()
temperature_in_celsius = sensor.get_temperature()
temperature_in_fahrenheit = sensor.get_temperature(W1ThermSensor.DEGREES_F)
temperature_in_all_units = sensor.get_temperatures([W1ThermSensor.DEGREES_C, W1ThermSensor.DEGREES_F, W1ThermSensor.KELVIN])

temp_f = 0
set_temp = 70

app = Flask(__name__)

@app.route("/", methods=['POST','GET'])
def main_page():
	t = sensor.get_temperature(W1ThermSensor.DEGREES_F) 
	current_temp = float("{0:.1f}".format(t))

	templateData = {
		'current_temp' : current_temp,
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
"""
def read_temp_raw():
	f = open(device_file, 'r')
	lines = f.readlines()
	f.close()
	return lines

def read_temp():
	global temp_f
	lines = read_temp_raw()
	while lines[0].strip()[-3:] != 'YES':
		time.sleep(0.2)
		lines = read_temp_raw()
	equals_pos = lines[1].find('t=')
	if equals_pos != -1:
		temp_string = lines[1][equals_pos+2:]
		temp_c = float(temp_string) / 1000.0
		temp_f = temp_c * 9.0 / 5.0 + 32.0
		return temp_f
	time.sleep(1)
"""
if __name__ == "__main__":
	app.run(host='0.0.0.0', port=80, debug=True,)
