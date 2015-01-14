#!/usr/bin/python
from flask import Flask, render_template, request, Response
from functools import wraps
import datetime
import time
import sys
import thread
import feedparser
import os

app = Flask(__name__)

@app.route("/")
def main_page():
	return render_template('index.html')


if __name__ == "__main__":
	app.run(host='0.0.0.0', port=80, debug=True)


