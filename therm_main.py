#!/usr/bin/python -d
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------------
#  RasTherm - Thermostat software for the Raspberry Pi
#  Author: Bert Zauhar, VE2ZAZ.   Web: http://ve2zaz.net
#  Version 1, March 2014
#  __      ________ ___  ______          ______             _   
#  \ \    / /  ____|__ \|___  /   /\    |___  /            | |  
#   \ \  / /| |__     ) |  / /   /  \      / /   _ __   ___| |_ 
#    \ \/ / |  __|   / /  / /   / /\ \    / /   | '_ \ / _ \ __|
#     \  /  | |____ / /_ / /__ / ____ \  / /__ _| | | |  __/ |_ 
#      \/   |______|____/_____/_/    \_\/_____(_)_| |_|\___|\__| 
 
# -----------------------------------------------------------------------------------
# Module Imports
# -----------------------------------------------------------------------------------
from flask import Flask, render_template, request, Response # Flask is the web server environment
from functools import wraps   # required for authentication functions
import datetime
import time
import sys
import thread  # note, "thread" rather than "threading"
import RPIO  # the RPIO package for GPIO control of Raspberry Pi's pins
import feedparser  # RSS feed access for outside temperature reading
from pychart import * # For temperature stats plotting
import os

# -----------------------------------------------------------------------------------
# Global variables definition and initialization
# -----------------------------------------------------------------------------------
current_temp = 21.0
set_temp = 21.0
current_humidity = 37
set_therm_mode = "heat" # heat, cool, off
set_program_mode = "programmed"  # manual, programmed
set_blower_program_mode = "manual"  # manual, programmed
current_operation = "idle" # active, idle
set_blower = "off"  # or on
set_override = ""
temp_offset = 0.5       # The temperature offset that triggers a heat or cool cycle.
temp_correction = 0  # A correction factor to apply to the temperature read by the temp sensor (if inaccurate).
off_border = "0"
heat_border = "0"
cool_border = "0"
blower_border = "0"
off_image_size = "40"
heat_image_size = "40"
cool_image_size = "40"
blower_image_size = "40"
blower_prog_image_size = "40"
blower_prog_border = "0"
prog_border = "0"
prog_image_size = "40"
prog_edit_img_size = "20"
reset_delay_count = 0
delay = 30
current_data_line = 0
sck = 22  # GPIO 22 (pin 15) is sensor sck
data = 27  # GPIO 27 (pin 13) is sensor data 
time_of_command_sent = 0
waiting_temp_data = False
waiting_humid_data = False
checksum_error_counter = 0
status_byte = ''
ec_current_cond = '- - -'
heat_relay = 4  # GPIO 4 (pin 7)
cool_relay = 23  # GPIO 23 (pin 16)
blower_relay = 24  # GPIO 24 (pin 18)
interrupt_input = 18 # GPIO 18 (pin 12)
watchdog_pulse = 25 # GPIO 25 (pin 22)    Used in the watchdog pulse script
app = Flask(__name__) # Needed
temp_ctr = 0

crc_table = [0, 49,
98, 83, 196, 245, 166, 151, 185, 136, 219,
234, 125, 76, 31, 46, 67, 114, 33, 16, 135,
182, 229, 212, 250, 203, 152, 169, 62, 15,
92,  109,  134,  183,  228,  213,  66,  115,  32,
17,  63,  14,  93,108,  251,  202,  153,  168,
197, 244, 167, 150, 1, 48, 99, 82, 124, 77,
30,  47,  184,  137,  218,  235,  61,  12,  95,
110,  249,  200,  155,  170,  132,  181,  230,
215, 64, 113, 34, 19, 126, 79, 28, 45, 186,
139,  216,  233,  199,  246,  165,  148,  3,  50,
97,  80,  187,  138,  217,  232,  127,  78,  29,
44, 2, 51, 96, 81, 198, 247, 164, 149, 248,
201,  154,  171,  60,  13,  94,  111,  65,  112,
35,  18,  133,  180,  231,  214,  122,  75,  24,
41, 190, 143, 220, 237, 195, 242, 161, 144,
7,  54,  101,  84,  57,  8,  91,  106,  253,  204,
159, 174, 128, 177, 226, 211, 68, 117, 38,
23, 252, 205, 158, 175, 56, 9, 90, 107, 69,
116, 39, 22, 129, 176, 227, 210, 191, 142,
221, 236, 123, 74, 25, 40, 6, 55, 100, 85,
194,  243,  160,  145,  71,  118,  37,  20,  131,
178, 225, 208, 254, 207, 156, 173, 58, 11,
88,  105,  4,  53,  102,  87,  192,  241,  162,
147,  189,  140,  223,  238,  121,  72,  27,  42,
193,  240,  163,  146,  5,  52,  103,  86,  120,
73,  26,  43,  188,  141,  222,  239,  130,  179,
224, 209, 70, 119, 36, 21, 59, 10, 89, 104,
255, 206, 157, 172]
 
# -----------------------------------------------------------------------------------
# Web authentication functions
# -----------------------------------------------------------------------------------
def check_auth(username, password):
# This function is called to check if a username / password combination is valid.
    return username == 'user' and password == 'rastherm'

def check_debug_auth(username, password):
# This function is called to check if a username / password combination is valid.
    return username == 'admin' and password == 'rastherm'

def authenticate():
# Sends a 401 response that enables basic auth"""
    return Response(
    'Could not verify your access level for that URL.\n'
    'You have to login with proper credentials', 401,
    {'WWW-Authenticate': 'Basic realm="Login Required"'})

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            time.sleep(3)  
            return authenticate()
        return f(*args, **kwargs)
    return decorated
    
def requires_debug_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_debug_auth(auth.username, auth.password):
            time.sleep(3)  
            return authenticate()
        return f(*args, **kwargs)
    return decorated

# -----------------------------------------------------------------------------------
# Here the various webpages and iframes are defined.
# -----------------------------------------------------------------------------------

# Main entry point of Website, only pops up the thermostat web page.
@app.route("/")
#@requires_auth # user/password required
def main_page():
   templateData = {
      'title' : 'RasTherm',
      }
   return render_template('RasTherm.html', **templateData)

# The real thermostat page, a pop up window.
@app.route("/popup_main.html")
#@requires_auth # user/password required
def popup_page():
   templateData = {
      'title' : 'RasTherm',
      }
   return render_template('popup_main.html', **templateData)
    
@app.route("/status_bar.html", methods=['GET'])
#@requires_auth # user/password required
def upd_status_bar():
   # Traduction française des status. Utiliser u'...' pour envoyer des variables avec accents au ficher HTML
   timeString = datetime.datetime.now().strftime("%A  %d/%m/%Y  %H:%M") # Obtain and format date and time string.
   if (set_therm_mode == 'heat'): set_therm_mode_f = 'Chauffage'  # Do a translation to French of the appropriate words for display on the status bar
   elif (set_therm_mode == 'cool'): set_therm_mode_f = 'Climatisation'         #   "
   elif (set_therm_mode == 'off'): set_therm_mode_f = u'Éteint'   
   if (set_program_mode == 'programmed'): set_program_mode_f = u'Programmé'
   elif (set_program_mode == 'manual'): set_program_mode_f = 'Manuel'
   if (set_override == 'override'): set_override_f = u'Ignoré'
   elif (set_override == ''): set_override_f = ''   
   if (current_operation == 'active'): current_operation_f = u'Actif'
   elif (current_operation == 'idle'): current_operation_f = u'Arrêté'  
   templateData = {   # Send status bar values to the webpage
      'time': timeString,
      'set_therm_mode': set_therm_mode_f,
      'set_program_mode': set_program_mode_f,
      'set_override' : set_override_f,
      'current_operation': current_operation_f
      }
   return render_template('status_bar.html', **templateData)
   
# Displays control buttons iframe
@app.route("/ctrl_buttons.html", methods=['POST','GET'])
#@requires_auth # user/password required
def load_button_colors():
   global off_border
   global heat_border
   global cool_border
   thick_border = "2"
   large_image = "40"
   small_image = "30"
   global off_image_size
   global heat_image_size
   global cool_image_size
   global blower_border
   global blower_image_size
   global prog_border
   global prog_image_size
   global prog_edit_img_size
   global blower_prog_image_size
   global blower_prog_border
   global set_program_mode
   global set_blower
   global set_blower_program_mode
   global set_therm_mode
   global set_override
   global current_operation
   global blower_relay
   
   if request.method == 'POST': # When a button was clicked:
      for key in request.form.keys(): # read the 'key' value
         pass
   else: key = ''
   if (key == 'off_button_pressed') or (set_therm_mode == "off" and request.method == 'GET'):   # If off button pressed, or if in off mode and this is just a page refresh (GET)
      off_border = thick_border  # Set buttons appearances accordingly
      heat_border = "0"          #  "
      cool_border = "0"       
      off_image_size = large_image
      heat_image_size = small_image
      cool_image_size = small_image
      set_therm_mode = "off"  # set to off mode
      if current_operation <> "idle":  # transition to idle because of the mode change
         current_operation = "idle"
         save_activity_data_point()  # save activity data point
      set_override = ""  # Cleaar the override condition
   elif (key == 'heat_button_pressed') or (set_therm_mode == "heat" and request.method == 'GET'): # If heat button pressed, or if in heat mode and this is just a page refresh (GET)
      off_border = "0"               # Set buttons appearances accordingly
      heat_border = thick_border     #  "
      cool_border = "0"
      off_image_size = small_image
      heat_image_size = large_image
      cool_image_size = small_image
      if request.method == 'POST':  # If button was pressed:
         reset_delay('')  # Start a new delay before applying mode change
         if (set_therm_mode == "cool") and (current_operation <> "idle"): # covers condition when jumping from cool to heat without going to off.
            current_operation = "idle"   # Go to idle
            save_activity_data_point()  # save activity data point           
      set_therm_mode = "heat"  # Set new mode to heat
   elif (key == 'cool_button_pressed') or (set_therm_mode == "cool" and request.method == 'GET'):
      off_border = "0"                # Set buttons appearances accordingly
      heat_border = "0"               #  " 
      cool_border = thick_border
      off_image_size = small_image
      heat_image_size = small_image
      cool_image_size = large_image
      if request.method == 'POST':  # If button was pressed:
         reset_delay('')  # Start a new delay before applying mode change
         if (set_therm_mode) == "heat" and (current_operation <> "idle"): # covers condition when jumping from heat to cool without going to off.
            current_operation = "idle"  # Go to idle
            save_activity_data_point()  # save activity data point          
      set_therm_mode = "cool"  # Set new mode to cool
   if key == ('blower_button_pressed'):  # Case when blower button is depressed
      if (set_blower == "off"):  # if blower is off
         set_blower = "on"    # turn it on
      else:                      # if blower is on
         set_blower = "off"      # turn it off
   if (set_blower == "on"):   # If blower is on 
      blower_border = thick_border     # change blower button appearance accordongly
      blower_image_size = large_image  # "
      RPIO.setup(blower_relay, RPIO.OUT, initial=RPIO.LOW)    # Put the GPIO pin in output mode and clear it (activate blower)                 
   elif (set_blower == "off") :  # if blower is off
      blower_border = "0"              # change blower button appearance accordongly
      blower_image_size = small_image  # "
      if (set_blower_program_mode == "manual"): RPIO.setup(blower_relay, RPIO.IN)   # Put the GPIO pin in input mode (de-activate blower)             
   if key == ('prog_button_pressed'):  # If Programmed button depressed
      if ((set_program_mode == "manual") and (int(datetime.datetime.now().strftime('%Y')) >= 2014)): # Checks that clock was set on NTP server before allowing programmed mode
         set_program_mode = "programmed"   # Set to programmed mode
      else:   # Otherwise, stay in manual mode.
         set_program_mode = "manual"  # "
   if (set_program_mode == "programmed"): # If in programmed mode, change programmed button apprerance accordingly
         prog_border = thick_border       #  "
         prog_image_size = large_image
   elif (set_program_mode == "manual"):  # If in programmed mode, change programmed button apprerance accordingly
         prog_border = "0"                #  "
         prog_image_size = small_image
         set_override = ""    # cleat the override mode
   if key == ('blower_prog_button_pressed'):  # If blower Programmed button depressed
      if (set_blower_program_mode == "manual"): 
         set_blower_program_mode = "programmed"   # Set to programmed mode
      else:   # Otherwise, stay in manual mode.
         set_blower_program_mode = "manual"  # "
   if (set_blower_program_mode == "programmed"): # If in programmed mode, change programmed button apprerance accordingly
         blower_prog_border = thick_border       #  "
         blower_prog_image_size = large_image
   elif (set_blower_program_mode == "manual"):  # If in programmed mode, change programmed button apprerance accordingly
         blower_prog_border = "0"                #  "
         blower_prog_image_size = small_image
   save_params(None) # Save parameters to file
   templateData = {
      'off_button_border' : off_border,
      'heat_button_border' : heat_border,
      'cool_button_border' : cool_border,
      'blower_button_border' : blower_border,
      'prog_button_border' : prog_border,
      'off_img_size' : off_image_size,
      'heat_img_size' : heat_image_size,
      'cool_img_size' : cool_image_size,
      'blower_img_size' : blower_image_size,
      'prog_img_size' : prog_image_size,
      'prog_edit_img_size' : prog_edit_img_size,
      'debug_img_size' : prog_edit_img_size,
      'blower_prog_img_size' : blower_prog_image_size,
      'blower_prog_button_border': blower_prog_border
      }
   return render_template('ctrl_buttons.html', **templateData)
   
# Displays current system action state (wind mill icons)
@app.route("/current_system_action.html")
#@requires_auth # user/password required
def update_action_icons():
   global current_operation
   global set_therm_mode
   global set_blower
   if (current_operation == 'active'):  # If system is active, the icons are animated gif icons
      if (not(RPIO.input(heat_relay))):
         icon = "/static/heat_active_icon.GIF"
      elif (not(RPIO.input(cool_relay))):
         icon = "/static/cool_active_icon.GIF"
   else:    # If system is idle, the icons are static gif icons
      icon = "/static/idle_icon.GIF"  
   if (not(RPIO.input(blower_relay))):  # If blower is active
      blower_icon = "/static/blower_active_icon.GIF"
   elif (RPIO.input(blower_relay)):
      blower_icon = "/static/blower_off_icon.GIF"  # this is an-all white icon, nothing gets displayed when the blower is off (useless)
   templateData = {
      'current_action_icon' : icon,
      'current_blower_icon' : blower_icon 
      }
   return render_template('current_system_action.html', **templateData)

# Displays current indoor and outdoor temperatures
@app.route("/current_temperature.html")
#@requires_auth # user/password required
def upd_current_temp():
   global current_temp
   global current_humidity
   global ec_current_cond
   global checksum_error_counter
   if (checksum_error_counter <> 0): # Case when sensor checksum errors are detected
      current_temp = '---'
      current_humidity = '---'
   try:
      if (datetime.datetime.now().strftime('%M')[1:] == '0') or (ec_current_cond == '- - -'): # Reads current wheather every 10 minutes (minutes ending with "0")
         d = feedparser.parse('http://weather.gc.ca/rss/city/qc-126_f.xml')  #  Get the weather RSS data from Environment Canada, Gatineau location
         s = d.entries[1]['title']   # Extract the current wheather condition string
         i = s.find(",")      # Provides the index where the comma is located. Temperature reading follows in the string. 
         ec_current_cond = s[i+2:len(s)]  # Environment Canada's Current Conditions field with the temperature extracted from the string.
   except:   # Case when it is not possible to read environnement Canada's RSS feed
      ec_current_cond = '- - -'  # blank display
   templateData = {
      'current_temperature' : current_temp,
      'current_humidity' : current_humidity,
      'ec_current_cond'  : ec_current_cond
      }
   return render_template('current_temperature.html', **templateData)

# Sets new temperature. Triggered by Set temperature dropdown menu change
@app.route("/set_temperature.html", methods=['POST','GET'])
#@requires_auth # user/password required
def set_temp_display():
   global set_temp
   global selection_array
   global set_override
   global set_program_mode
   if request.method == 'POST':  # HTML Post process as a result of the dropdown menu update 
      set_temp = float(request.form['set_temp_dropdown']) # read new temperature from dropdown menu item selected
      reset_delay('') # Impose a delay before applying new temperature
      if set_program_mode == "programmed":  # If in programmed mode, enable override mode
         set_override = 'override'
   save_params(None) # Save parameters to file
   templateData = {}
   for i in range(1,31): # render dropdown menu items (temperatures)
      templateData["s"+ str(i) + "selected"] = ' ' # fill with spaces to erase previous dropdown selection
   templateData["s"+ str(int((set_temp * 2) - 29))  + "selected"] = "selected"  # put "selected" in the right HTML dropdown location.
   return render_template('set_temperature.html', **templateData)

# Launches the program editor page and copies the program data to editable text boxes
@app.route("/launch_program_editor.html")
@requires_debug_auth # user/password required
def launch_programs():
   heat_cfg_file = open('./heat_program.cfg','r') # Open heat program configuration file for reading
   cool_cfg_file = open('./cool_program.cfg','r') # Open cool program configuration file for reading
   blower_cfg_file = open('./blower_program.cfg','r') # Open blowerprogram configuration file for reading
   templateData = {
      'heat_prog_data' : heat_cfg_file.read(),  # Fill heat textbox with current program settings
      'cool_prog_data' : cool_cfg_file.read(),   # Fill cool textbox with current program settings
      'blower_prog_data' : blower_cfg_file.read()   # Fill cool textbox with current program settings
      }
   heat_cfg_file.close()  # close heat program configuration file
   cool_cfg_file.close()  # close cool program configuration file
   blower_cfg_file.close()  # close cool program configuration file
   return render_template('launch_program_editor.html', **templateData)

# Transfers new programming data to heat program file
@app.route("/heat_submit_button.html", methods=['POST'])
@requires_debug_auth # user/password required
def update_heat_programs():
   heat_cfg_file = open('./heat_program.cfg','w')  # Open heat program configuration file for writing
   heat_cfg_file.write(request.form['heat_textarea'])  # transfer textbox data to file
   heat_cfg_file.close()  # close heat program configuration file
   templateData = {
      }
   return render_template('heat_submit_button.html', **templateData)

# Transfers new programming data to cool program file
@app.route("/cool_submit_button.html", methods=['POST'])
@requires_debug_auth # user/password required
def update_cool_programs():
   heat_cfg_file = open('./cool_program.cfg','w')  # Open program configuration file for writing
   heat_cfg_file.write(request.form['cool_textarea'])  # transfer textbox data to file
   heat_cfg_file.close()  # close cool program configuration file
   templateData = {
      }
   return render_template('cool_submit_button.html', **templateData)

# Transfers new programming data to blower program file
@app.route("/blower_submit_button.html", methods=['POST'])
@requires_debug_auth # user/password required
def update_blower_programs():
   blower_cfg_file = open('./blower_program.cfg','w')  # Open program configuration file for writing
   blower_cfg_file.write(request.form['blower_textarea'])  # transfer textbox data to file
   blower_cfg_file.close()  # close cool program configuration file
   templateData = {
      }
   return render_template('blower_submit_button.html', **templateData)

@app.route("/launch_debug.html", methods=['GET','POST'])
@requires_debug_auth  #  requires userid and password to access
def launch_debug_page():  # Just render the debug page
   global temp_offset
   global temp_correction
   if request.method == 'POST':  # HTML Post process   # This part covers the buttons that submit a new numerical value 
      temp_offset = float(request.form['temp_offset'])
      temp_correction = float(request.form['temp_correction'])
   templateData = {
      'temp_offset' : str(temp_offset),
      'temp_correction': str(temp_correction)
      }
   save_params(None) # Save parameters to file
   return render_template('launch_debug.html', **templateData)


@app.route("/debug_buttons/<button_pressed>", methods=['GET'])  # button_pressed can take variable value from 1 to 7, or a known variable value
@requires_debug_auth  #  requires debug userid and password to access
def execute_debug_command(button_pressed):
   import subprocess
   global temp_offset
   global temp_correction
   display_debug_result = ''
   if (button_pressed == 'reboot'):  # Pi reboot request
      command = "/usr/bin/sudo /sbin/shutdown -r now"                      # Send command to OS
      process = subprocess.Popen(command.split(), stdout=subprocess.PIPE)  #  "
      output = process.communicate()[0]  # Read back process console echo
      print output # print it to console
      result_message = u'   Reboot exécuté!'
   elif (button_pressed == 'shutdown'):  # Pi shutdown request
      command = "/usr/bin/sudo /sbin/shutdown -h now"                      # Send command to OS
      process = subprocess.Popen(command.split(), stdout=subprocess.PIPE)  #  "
      output = process.communicate()[0]  # Read back process console echo
      result_message = u'   Shutdown exécuté!'
      print output  
   elif ((int(button_pressed) >=1) and (int(button_pressed) <=7)): # If one of the plot buttons is pressed
      day = button_pressed # extract day number from HTML value returned
      plot_temp_stats(day) # Produce a new plot file
      display_debug_result = '/static/' + day + '_temp_plot.pdf' # Show the plot in the browser (send file name to HTML)
      result_message = day + u'_temp_plot.pdf créé!'
   templateData = {
      'display_debug_result': display_debug_result,
      'result_message': result_message
      }
   return render_template('debug_buttons.html', **templateData)

# -----------------------------------------------------------------------------------
# Sensor functions:  This is for the SHT10 Temperature/Humidity sensor
# -----------------------------------------------------------------------------------

#Sends one pulse to the SHT10
def pulse_sck(none):
   global sck
   RPIO.output(sck, True)
   time.sleep(0.001)
   RPIO.output(sck, False)
   time.sleep(0.001)

#Sends one bit to the SHT10
def send_data_bit(bit):
   global data
   RPIO.output(data, bit)
   time.sleep(0.001)

# Sends one command to the SHT10
def send_sensor_command(command_type):
   global data
   global sck
   none = ' '   # must send something to a function...
   RPIO.setup(data, RPIO.OUT, initial=RPIO.HIGH)  # Reset bus by sending 10 pulses
   RPIO.setup(sck, RPIO.OUT, initial=RPIO.LOW)    # "
   for i in range(0,11):    pulse_sck(none)      # "
  # Send command to measure temperature
   # Tx start sequence
   RPIO.setup(sck, RPIO.OUT, initial=RPIO.HIGH)  # Set up sck signal with initial value of 1
   time.sleep(0.001)
   RPIO.setup(data, RPIO.OUT, initial=RPIO.LOW)  # Set up data line. Gives a high to low transition (pull up on floating line)
   time.sleep(0.001)
   RPIO.output(sck, False) # low pulse on sck
   time.sleep(0.001)
   RPIO.output(sck, True)  #  high pulse on sck
   time.sleep(0.001)
   send_data_bit(True)     # raise data line
   RPIO.output(sck, False)  #  low on sck
   time.sleep(0.001)
   # Send actual command
   send_data_bit(False)
   pulse_sck(none)      # 0
   pulse_sck(none)      # 0      
   pulse_sck(none)      # 0      
   pulse_sck(none)      # 0      
   pulse_sck(none)      # 0      
   if command_type == 'Temperature': # Temperature reading request
      pulse_sck(none)      # 0      
      send_data_bit(True)
      pulse_sck(none)      # 1      
      RPIO.output(sck, True)      # 1      (right after this, data line pulled low after 8th bit by sensor to acknowledge reception)
   elif command_type == 'Humidity': # Humidity reading request
      send_data_bit(True)
      pulse_sck(none)      # 1      
      send_data_bit(False)
      pulse_sck(none)      # 0      
      send_data_bit(True)
      RPIO.output(sck, True)      # 1      (right after this, data line pulled low after 8th bit by sensor to acknowledge reception)
   elif command_type == 'Status': # Status Byte request
      send_data_bit(True)
      pulse_sck(none)      # 1      
      pulse_sck(none)      # 1      
      RPIO.output(sck, True)      # 1      (right after this, data line pulled low after 8th bit by sensor to acknowledge reception)
   # release data line control by sensor   
   RPIO.setup(data, RPIO.IN)  # sets data line to read back from sensor
   time.sleep(0.001)
   RPIO.output(sck, False)      # 1      (data line pulled low after 8th bit by sensor to acknowledge reception)
   time.sleep(0.001)
   pulse_sck(none)    # acknowledge pulse sent

 # Reads the sensor's status register
def read_sensor_status_reg(none):
   data_word = '' # initializes binary string to empty
   RPIO.setup(data, RPIO.IN)  # sets data line to read back from sensor
   for j in range(1,9):  # read 8 bits
      bit = "0"      # start with an assumed read bit of 0
      if (RPIO.input(data) == True): bit = "1"  # if read bit is high, change bit to 1
      data_word = data_word + bit  # add bit to accumulated bit message
      pulse_sck(none)   # pulse clock to force output of next bit
   RPIO.setup(data, RPIO.OUT, initial=RPIO.HIGH)  # do not send ACK, not interested here in checksum reading
   time.sleep(0.001)
   pulse_sck(none)  # send a lo-high-low transition to clock line, ending sensor transmission of status byte
   return data_word

 # Read back SHT10 data
def read_sensor_data(none):
   global waiting_temp_data
   global status_byte
   global temp_ctr
   data_word = '' # initializes binary string to empty
   for i in range(1,4):  #read three bytes
      RPIO.setup(data, RPIO.IN)  # sets data line to read back from sensor
      for j in range(1,9):  #read 8 bits
         bit = "0" # start with an assumed read bit of 0
         if (RPIO.input(data) == True): bit = "1"  # if read bit is high, change bit to 1
         data_word = data_word + bit  # add bit to accumulated bit message
         pulse_sck(none)   # pulse clock to force output of next bit
      RPIO.setup(data, RPIO.OUT, initial=RPIO.LOW)  # gives a high to low ACK transition (pull up on floating line).
      time.sleep(0.001)
      pulse_sck(none)  # send a lo-high-low transition to clock line, sending ACK to sensor
   msb_data_byte = '0b' + data_word[:8]      # split the three bytes read into individual registers
   lsb_data_byte = '0b' + data_word[8:-8]    # "
   chksum_data_byte = '0b' + data_word[16:]  # "
     # Calculate the checksum, as per SHT10 CRC Calculation datasheet
   checksum = '0b' + status_byte[4:][::-1] + '0000' # keep 4 LSb of status byte, reverse them and add 4 zeros.
   if (waiting_temp_data): command_byte = '0b00000011' # Use the right sent command in the CRC calculation (temperature or humidity command)
   else: command_byte = '0b00000101'                   # "
   checksum = crc_table[int(checksum,2) ^ int(command_byte,2)] # XOR of checksum and command byte
   checksum = crc_table[checksum ^ int(msb_data_byte,2)]  # XOR of resulting interim checksum and MSB byte
   checksum = crc_table[checksum ^ int(lsb_data_byte,2)]  # XOR of resulting interim checksum and LSB byte
   checksum = '0b' + ("{0:08b}".format(checksum))[::-1]  # convert interim checksum to binary representation and reverse its bit order
   if (int(checksum,2)) == (int(chksum_data_byte,2)):   # Check if calculated checksum matches transmitted checksum
      temp_ctr=temp_ctr+1
      print 'Checksum OK No: ' + str(temp_ctr)
      return float(int(msb_data_byte + lsb_data_byte[2:], 2))
   else: 
      print 'Checksum ERROR !!!'
      temp_ctr = 0
      return 0

# -----------------------------------------------------------------------------------
# Long Delay functions: used to delay the temperature setting change.
# -----------------------------------------------------------------------------------

# Resets counter to initiate long delay.
def reset_delay(none):
   global reset_delay_count
   reset_delay_count = time.time() # update delay count with current time in seconds

# Verifies whether long delay has elapsed   
def check_delay(none):
   global reset_delay_count
   global delay
   if ((time.time() - reset_delay_count) > delay):  # if current time minus delay count is larger than set delay
      return True  
   else: 
      return False
      
# -----------------------------------------------------------------------------------
# This function saves the configuration (current function status) to disk for next time program launch retrieval      
def save_params(none):
      global set_temp
      global set_therm_mode
      global set_program_mode
      global set_blower     
      global set_blower_program_mode
      global temp_offset
      global temp_correction
      saved_file = open('./saved.cfg','w') # Open saved configuration file for writing
      saved_file.write(str(set_temp) + '\n')      # save important parameters
      saved_file.write(set_therm_mode + '\n')
      saved_file.write(set_program_mode + '\n')
      saved_file.write(set_blower + '\n')
      saved_file.write(set_blower_program_mode + '\n')
      saved_file.write(str(temp_offset) + '\n')
      saved_file.write(str(temp_correction) + '\n')
      saved_file.close()   # Close file
 
# -----------------------------------------------------------------------------------
# This function execute some background python code every two seconds. It is used to run the idle loop code that manages the thermostat parameters
# between web page refreshes. 
def background_code():
   global current_temp
   global current_humidity
   global set_therm_mode
   global set_temp
   global temp_offset
   global current_operation
   global set_program_mode
   global set_blower_program_mode
   global data_line_ctr
   global set_override
   global current_data_line
   global time_of_temp_command_sent
   global heat_relay
   global cool_relay
   global data_number
   global temp_data
   global waiting_temp_data
   global waiting_humid_data
   global status_byte
   global checksum_error_counter
   global temp_correction
   while True:
      time.sleep(2)  # function executed every 2 seconds
   # Long term temperature sensor transmission error check   
      if (checksum_error_counter >= 15):  # If consecutive sensor errors are logged for more than 1 minute... 
         set_therm_mode = "off"   # turn off system
   # Heat mode trigger points and relay control
      if set_therm_mode == "heat": # Heat mode enabled
         RPIO.setup(cool_relay, RPIO.IN)  #  Set the cool relay to input (de-activate) 
         if (current_temp <= (set_temp - temp_offset)) and (current_operation == 'idle') and (check_delay('')):  # transition operation from idle to active when temperature difference condition is met, after a delay
            current_operation = 'active'  # become active
            RPIO.setup(heat_relay, RPIO.OUT, initial=RPIO.LOW)   # activate heat relay         
            save_activity_data_point()  # Save a data point in the activity log file 
         elif (current_temp >= (set_temp + temp_offset)) and current_operation == 'active': # transition operation from active to idle when temperature difference condition is met
            current_operation = 'idle' # become inactive
            RPIO.setup(heat_relay, RPIO.IN)        # de-activate heat relay         
            save_activity_data_point()  # Save a data point in the activity log file 
   # Cool mode trigger points  and relay control
      elif set_therm_mode == "cool":  # Cool mode enabled
         RPIO.setup(heat_relay, RPIO.IN)    #  Set the heat relay to input (de-activate) 
         if (current_temp >= (set_temp + temp_offset)) and (current_operation == 'idle') and (check_delay('')):  # transition operation from idle to active when temperature difference condition is met, after a delay
            current_operation = 'active'   # become active
            RPIO.setup(cool_relay, RPIO.OUT, initial=RPIO.LOW)         # activate cool relay               
            save_activity_data_point()  # Save a data point in the activity log file 
         elif (current_temp <= (set_temp - temp_offset)) and current_operation == 'active': # transition operation from active to idle when temperature difference condition is met
            current_operation = 'idle'   # become inactive
            RPIO.setup(cool_relay, RPIO.IN)    # de-activate cool relay   
            save_activity_data_point()  # Save a data point in the activity log file 
   # Off mode relay control
      elif set_therm_mode == "off":  # case when the mode is 'off'
         RPIO.setup(heat_relay, RPIO.IN)    # de-activate heat relay   
         RPIO.setup(cool_relay, RPIO.IN)    # de-activate cool relay   

   # Retrieve current date and time
      now = datetime.datetime.now() # read currrent date and time
      current_day = int(now.strftime('%w')) + 1 # datetime returns 0 to 6 for weekday range. We want 1 to 7
      current_hour = int(now.strftime('%H'))  # hours
      current_minute = float(now.strftime('%M')) # minutes
      current_time = current_hour + (current_minute/60) # hours + fraction of hours

   # Programmed mode control (follow programmed schedule)
      if (set_program_mode == "programmed") and (set_therm_mode <> "off"):  # condition when in programmed mode and not in off therm mode
         if set_therm_mode == "heat": # if in heat mode
            cfg_file = open('./heat_program.cfg','r') # Open programmed configuration file for reading
         elif set_therm_mode == "cool": # if in cool mode
            cfg_file = open('./cool_program.cfg','r') # Open programmed configuration file for reading
         data_line_ctr = 0  # reset line counter
         while True:   # Program File read loop
            while True:  # repeat reading until valid data line
               data_line = cfg_file.readline()  # reads one line
               if data_line[0:1] <> '#':  # skips the comment lines
                  break # if not a comment line, exit this loop
            data_line_ctr = data_line_ctr + 1 # increment line counter
            if data_line == '':  # end of file reached ?
               break  # exit big file loop if end of file reached
            if (int(data_line[0:1]) == current_day):  # Retrieve day number from data line
               if (int(data_line[2:4]) + (float(data_line[5:7])/60) <= current_time) and (int(data_line[8:10]) + (float(data_line[11:13])/60) >= current_time): # Validate whether data line covers the current day and time
                  if (set_override <> 'override') or (set_override == 'override' and data_line_ctr > current_data_line):  # If not in override, or if in override but a new program period (data line) applies
                     set_temp = float(data_line[14:18])  # apply new set temperature
                     set_override = ''  # remove override mode
                     current_data_line = data_line_ctr # save the data line counter as the new current (applicable) data line
                     break # exit big file loop, as program has found the applicable data line
         cfg_file.close()  # close confiug file

   # Blower Programmed mode control (follow programmed schedule)
      if (set_blower_program_mode == "programmed"):  # condition when in blower programmed mode
         cfg_file = open('./blower_program.cfg','r') # Open programmed configuration file for reading
         data_line_ctr = 0  # reset line counter
         while True:   # Program File read loop
            while True:  # repeat reading until valid data line
               data_line = cfg_file.readline()  # reads one line
               if data_line[0:1] <> '#':  # skips the comment lines
                  break # if not a comment line, exit this loop
            data_line_ctr = data_line_ctr + 1 # increment line counter
            if data_line == '':  # end of file reached ? (meaning no entry matches current day and time)
               if (set_blower == "off"): # turn off blower only if not manually turned on
                  RPIO.setup(blower_relay, RPIO.IN)   # Put the GPIO pin in input mode (de-activate blower)             
               break  # exit big file loop if end of file reached
            if (int(data_line[0:1]) == current_day):  # Retrieve day number from data line
               if (int(data_line[2:4]) + (float(data_line[5:7])/60) <= current_time) and (int(data_line[8:10]) + (float(data_line[11:13])/60) >= current_time): # Validate whether data line covers the current day and time
                  RPIO.setup(blower_relay, RPIO.OUT, initial=RPIO.LOW)    # Put the GPIO pin in output mode and clear it (activate blower)                 
                  break # exit big file loop, as program has found the applicable data line
         cfg_file.close()  # close confiug file
         
   #Sensor control
      if not(waiting_temp_data) and not(waiting_humid_data): # Time to request a new temperature data
         send_sensor_command('Status')
         status_byte = read_sensor_status_reg('')  # Used in checksum calculation routine
         send_sensor_command('Temperature')  # Send temperature read command
         time_of_command_sent = time.time()  # save current time for delay calculation
         waiting_temp_data = True  # raise the waiting for temperature flag
      elif waiting_temp_data and (time.time() - time_of_command_sent >= 1): # Time to read temperature data (expired wait for data ready)
         data_float = read_sensor_data(' ')  # read sensor data
         if (data_float <> 0): 
            current_temp = round((-39.65 + (0.01 * data_float)) + temp_correction, 1)  # calculate current temperature and assign value if no errors were detected. Temperature expressed in degrees Celsius.
               # To convert to Fahrenheit, do: current_temp = round((9/5 * (-39.65 + (0.01 * data_float))) + 32 + temp_correction, 1) 
            checksum_error_counter = 0
         else: checksum_error_counter = checksum_error_counter + 1  # Condition where a checksum error occured. Do not update current temperature and increment error counter
         send_sensor_command('Status')
         status_byte = read_sensor_status_reg('')
         send_sensor_command('Humidity')  # ...and request new humidity read command
         time_of_command_sent = time.time() # save current time for delay calculation
         waiting_temp_data = False  # lower the waiting for temperature flag
         waiting_humid_data = True  # raise the waiting for humidity flag
      elif waiting_humid_data and (time.time() - time_of_command_sent >= 1): # Time to read humidity data (expired wait for data ready)
         data_float = read_sensor_data(' ')  # read sensor data
         current_humidity = round((-2.0468 + (0.0367 * data_float) + (-1.5955E-6 * data_float *data_float)), 0) # calculate current humidity
         waiting_temp_data = False   # lower the waiting for temperature flag
         waiting_humid_data = False  # lower the waiting for humidity flag
         
#      current_temp = 20 + round(float(datetime.datetime.now().strftime('%M')[1:2])/3,1)

# -----------------------------------------------------------------------------------
# Function that gets executed when an interrupt is detected on the TCP/IP port.
# Phone system is sending a command and this function acts upon.
def socket_callback(socket, val):
   global set_program_mode
   global set_therm_mode
   global set_temp
   global set_override
   global current_operation
   error_detected = False
   try:  # Check whether it is a new temperature setting received, or another command
      temp = float(val) # check if a temperature setting was received
      set_temp = temp   # if yes, set new temperature
      if set_program_mode == "programmed": set_override = 'override'  # this force the program-override mode
      reset_delay('') # start a new long delay
      socket.send("OK") # send OK back to phone system
   except:  # Not a temperature setting, a command received instead
      if  val == 'get_curr_temp': # current temperature requested
         socket.send('temp' + str(current_temp)) # send it back
      elif  val == 'get_set_temp': # set temperature requested
         socket.send('temp' + str(set_temp)) # send it back
      elif  val == 'get_status': # system status requested
         socket.send('stat' + set_therm_mode + '_' + set_program_mode + '_' + current_operation) # send formatted system status string
      elif val == 'programmed':
         set_program_mode = 'programmed' # programmed mode invoked
         socket.send("OK")
      elif val == 'manual':  
         set_program_mode = 'manual'  # manual mode invoked
         socket.send("OK")
      elif val == 'off':
         set_therm_mode = 'off' # off mode invoked
         socket.send("OK")
      elif val == 'heat':  # thermal heat mode invoked
         set_therm_mode = 'heat'
         socket.send("OK")
      elif val == 'cool':
         set_therm_mode = 'cool'  # thermal cool mode invoked
         socket.send("OK")
      else: socket.send("ERROR")  # error decoding, send ERROR back
   RPIO.close_tcp_client(socket.fileno())
   save_params(None) # Save parameters to file

# -----------------------------------------------------------------------------------
# Generates a 0.5 Hz square wave to show life to external watchdog PIC micro-controller and trigger an interrupt to run the background code.
# To be run in a separate thread.
def watchdog_pulse_func():
   global watchdog_pulse
   RPIO.setup(watchdog_pulse, RPIO.OUT, initial=RPIO.LOW)  # set pin as output
   while (True): # endless loop
      RPIO.output(watchdog_pulse, False) # low pulse on watchdog_pulse
      time.sleep(1) # wait one second
      RPIO.output(watchdog_pulse, True)  #  high "  "  "
      time.sleep(1) # wait one second

# -----------------------------------------------------------------------------------
# Function running as a separate thread. Write current temperature data to a log file every 60 seconds. 
# Keeps log files for 7 days and then overwrites them. 
def save_temp_data_point():
   global current_temp
   while True:  # endless loop
      time.sleep(60)  # wait 60 seconds
      date_and_time = datetime.datetime.now().strftime('%w,%d/%m/%Y,%H:%M') # extract current date and time data in the proper format from the system
      today = str(int(date_and_time[0]) + 1)   # get the day number from 1 to 7
      if (os.path.exists('./logs/' + today + '_temp_data.txt')): # Does daily log file exist?
         if (time.time() - os.path.getmtime('./logs/' + today + '_temp_data.txt') > 86401): # Check if existing log file has a modification time (in seconds) older than one day. If yes, it is last week's file so delete it first.
            os.remove('./logs/' + today + '_temp_data.txt') #  Delete file
      temp_data_file = open('./logs/' + today + '_temp_data.txt', 'a') # Open log file for appending
      temp_data_file.write(today + date_and_time[1:] + ',' + str(current_temp) + '\n') # append data point
      temp_data_file.close() # close daily log file.
      
# -----------------------------------------------------------------------------------
# Function called to save the active and idle times for analysis.
# Keeps log files for 7 days and then overwrites them. 
def save_activity_data_point():
   global current_operation
   date_and_time = datetime.datetime.now().strftime('%w,%d/%m/%Y,%H:%M') # extract current date and time data in the proper format from the system
   today = str(int(date_and_time[0]) + 1)   # get the day number from 1 to 7
   if (os.path.exists('./logs/' + today + '_activity_data.txt')): # Does daily log file exist?
      if (time.time() - os.path.getmtime('./logs/' + today + '_activity_data.txt') > 86401): # Check if existing log file has a modification time (in seconds) older than one day. If yes, it is last week's file so delete it first.
         os.remove('./logs/' + today + '_activity_data.txt') #  Delete file
   activity_data_file = open('./logs/' + today + '_activity_data.txt', 'a') # Open log file for appending
   if (current_operation == 'active'): activity_flag = '1'
   else: activity_flag = '0'
   activity_data_file.write(today + date_and_time[1:] + ',' + activity_flag + '\n') # append data point
   activity_data_file.close() # close daily log file.

# -----------------------------------------------------------------------------------
# Function that generates a .pdf plot file for the seven days of existing log data, one .pdf file per day.
def plot_temp_stats(day): 
      if os.path.exists('./logs/' + day + '_temp_data.txt'): # Check if file exists
         temp_data = [] # Create a collection of data points for plotting
         data_line = 'nil'
         data_file = open('./logs/' + day + '_temp_data.txt','r')  # open daily log file
         file_date = data_file.readline()[2:12].replace('/','_') # must replace / character otherwise pychart rejects.
         data_file.close() # Close daily log file
         data_file = open('./logs/' + day + '_temp_data.txt','r')  # open daily log file
         while True: # read all lines of the daily temperature log file
            data_line = data_file.readline() # read one line
            if (data_line == ''): break # if end of file is reached, get out of this loop
            time_of_day = float(data_line[13:15]) + round(float(data_line[16:18])/60,2) # extract time in hours and fraction of hours in decimal (hh.xx)
            temp_value = float(data_line[19:23])  # extract temperature
            temp_data.extend([(time_of_day,temp_value)])  # append temperature value to array
         if os.path.exists('./logs/' + day + '_activity_data.txt'): # Check if file exists
            activ_data = [] # Create a collection of data points for plotting
            data_line = 'nil'
            data_file = open('./logs/' + day + '_activity_data.txt','r')  # open daily log file
            while True: # read all lines of the daily log file
               data_line = data_file.readline() # read one line
               if (data_line == ''): break # if end of file is reached, get out of this loop
               time_of_day = float(data_line[13:15]) + round(float(data_line[16:18])/60,2) # extract time in hours and fraction of hours in decimal (hh.xx)
               activ_value = float(data_line[19:20])  # extract temperature
               # Define bar-like points to show system activity on plot
               if (activ_value == 1):  
                  activ_value = 15.0
                  activ_data.extend([(time_of_day,activ_value)])  # append activity value to array
                  activ_value = 29.5
                  activ_data.extend([(time_of_day,activ_value)])  # append activity value to array
               else: 
                  activ_value = 29.5
                  activ_data.extend([(time_of_day,activ_value)])  # append activity value to array
                  activ_value = 15.0
                  activ_data.extend([(time_of_day,activ_value)])  # append activity value to array               
#               activ_data.extend([(time_of_day,activ_value)])  # append activity value to array
         # Plot .pdf file
         fd = file('./static/' + day + '_temp_plot.pdf', "w")
         can = canvas.init(fd,'pdf')   # .png also possible
         theme.get_options()
         theme.scale_factor = 1
         theme.default_line_width = 0.001
         theme.reinitialize() # Must be called so that the above variables get updated
         xaxis = axis.X(format="/hL%d", tic_interval = 1, tic_len = 10, minor_tic_interval = 0.25, minor_tic_len = 5, label="Time of day (hours) on " + file_date)
         yaxis = axis.Y(tic_interval = 1, label="Indoor Temperature (C)")
         ar = area.T(x_axis=xaxis, x_range=(0,24), y_axis=yaxis, y_range=(15,30), y_grid_interval=1, size=(2000,300), legend=None)
         ar.add_plot(line_plot.T(data=temp_data, ycol=1, tick_mark=tick_mark.circle1),line_plot.T(data=activ_data, ycol=1, tick_mark=tick_mark.circle1))
         ar.draw()
         can.close()
         data_file.close() # Close daily log file

# -----------------------------------------------------------------------------------
# Main executed code starts here
# -----------------------------------------------------------------------------------
if __name__ == "__main__":
   RPIO.setwarnings(False)  # Turn off RPIO debug messages
   RPIO.cleanup() # Cleanup RPIO
   RPIO.setup(heat_relay, RPIO.IN) # Release the thermostat relays before anything else
   RPIO.setup(cool_relay, RPIO.IN) #    "
   RPIO.setup(blower_relay, RPIO.IN)     
   try:  # Load parameters from file at startup
      saved_file = open('./saved.cfg','r') # Open saved configuration file for reading
      set_temp = float(saved_file.readline()[:-1]) # Load set temperature
      set_therm_mode = saved_file.readline()[:-1]  # must remove LF
      set_program_mode = saved_file.readline()[:-1] #load set program mode
      set_blower = saved_file.readline()[:-1] # load blower setting (on or off)
      set_blower_program_mode = saved_file.readline()[:-1] # load blower program setting
      temp_offset = float(saved_file.readline()[:-1])
      temp_correction = float(saved_file.readline()[:-1])
      saved_file.close() # close file
   except IOError: # Case where parameters retrieval fails
      set_temp = 21.0 # 21 is a reasonable default temperature
      set_therm_mode = "heat" # heat, cool, off
      set_program_mode = "programmed"  # manual, programmed
      set_blower = "off"  # or on
   if (int(datetime.datetime.now().strftime('%Y')) < 2014):  # Checks that clock was set to NTP server, otherwise force the manual mode.
      set_program_mode = 'manual' 
   reset_delay('') # start a new long delay 
   thread.start_new_thread(watchdog_pulse_func, ())  # Generates watchdog pulses as a separate thread.
   thread.start_new_thread(background_code, ())  # run background code as a separate thread
   thread.start_new_thread(save_temp_data_point, ())  # run the temperature data save routine as a separate thread
   RPIO.add_tcp_callback(8080, socket_callback) # enable interrupts from the TCP/IP port (phone system communication with this RasTherm)
   RPIO.wait_for_interrupts(threaded=True) # Thread that monitors for the TCP/IP port interrupt
   print(" ")
   print("  Setup completed, Launching Web server now...")
   app.run(host='0.0.0.0', port=80, debug=False)  # Here, the Flask web server is launched

# End of python script
