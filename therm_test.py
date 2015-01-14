#!/usr/bin/python
from flask import Flask, render_template, request, Response
from functools import wraps
import datetime
import time
import sys
import thread
import feedparser
import os

current_temp = 72

app = Flask(__name__)

@app.route("/")
def main_page():

	templateData = {
		'current_temperature' : current_temp
	}
	return render_template('main.html', **templateData)
@app.route("/override")
def override():
	return render_template('override.html')


if __name__ == "__main__":
	app.run(host='0.0.0.0', port=80, debug=True)


