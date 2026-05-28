##Setup
import digitalio
import board
import os
import adafruit_bme680
from adafruit_ads1x15 import ADS1015, AnalogIn, ads1x15
import cv2

import neopixel

import time
from datetime import datetime
from flask import Flask, Response, jsonify, send_from_directory, request, render_template, redirect, url_for
import threading
import linecache
import shutil
import sys
import json
import subprocess

from collections import deque
from tflite_runtime.interpreter import Interpreter
import numpy as np
import random

# Load TFLite root classification model and allocate tensors
MODEL = "Root_Classification_Model.tflite"
interpreter = Interpreter(model_path=MODEL)
interpreter.allocate_tensors()
input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()
_, h, w, c = input_details[0]['shape']  # Extract expected input dimensions from model

# Rolling window for smoothing AI predictions over time
avg_window = 20
predictions = deque(maxlen=avg_window)

# Initialize I2C bus and BME680 environmental sensor (temp, humidity, pressure, VOC)
i2c_bus = board.I2C()
bme680 = adafruit_bme680.Adafruit_BME680_I2C(i2c_bus, address=0x77)

# Read ambient pressure from config (line 1); used for altitude-corrected pressure readings
try:
     line1 = linecache.getline("/home/nanolab/config.txt", 1)
     ambient_pressure = float(line1)
except Exception as e:
     ambient_pressure = 1013  # Default to standard sea-level pressure (hPa)
     print("Please Configure Settings")
bme680.seaLevelhPa = ambient_pressure

# Read module configuration name from config (line 2); determines which webpage set to serve
try:
     line2 = linecache.getline("/home/nanolab/config.txt", 2)
     module_config = str(line2)
     module_config = module_config.replace("\n", "")
except Exception as e:
     module_config = "aeroponictest"
     print("Please Configure Settings")

# Read NeoPixel brightness from config (line 3)
try:
     line3 = linecache.getline("/home/nanolab/config.txt", 3)
     bright = float(line3.strip())
except Exception as e:
     bright = 0.1  # Default to 10% brightness
     print("Please Configure Settings")

# Initialize NeoPixel LED strip (20 LEDs on GPIO D18) and set to warm white for viewing
pixelcount = 16
pixels = neopixel.NeoPixel(board.D18, pixelcount, brightness=bright, auto_write=False)
pixels.fill((255, 200, 180))
pixels.show()

# Read photo interval (in seconds) between test shots from config (line 4)
try:
     line4 = linecache.getline("/home/nanolab/config.txt", 4)
     testphotogap = float(line4.strip())
except Exception as e:
     testphotogap = 0.5  # Default to 0.5 seconds between test photos
     print("Please Configure Settings")

# Read total number of photos to take per test session from config (line 5)
try:
     line5 = linecache.getline("/home/nanolab/config.txt", 5)
     requestedphotocount = int(line5.strip())
except Exception as e:
     requestedphotocount = 10  # Default to 10 photos per test
     print("Please Configure Settings")

# Read monitoring interval (in hours) from config (line 6); converted to seconds
try:
     line6 = linecache.getline("/home/nanolab/config.txt", 6)
     monitortime = float(line6.strip())
     monitortime = ((monitortime * 60) * 60)  # Convert hours -> seconds
except Exception as e:
     monitortime = 21600  # Default to 6 hours
     print("Please Configure Settings")

# Initialize Flask app, pointing to the correct webpage folder for this module
app = Flask(__name__, template_folder='../webpages/' + module_config.strip())
WEB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../webpages/" + module_config.strip())
WEB_DIR = os.path.abspath(WEB_DIR)

def find_camera_index(usb_port):
    result = subprocess.run(['v4l2-ctl', '--list-devices'], capture_output=True, text=True)
    lines = result.stdout.split('\n')
    for i, line in enumerate(lines):
        if usb_port in line:
            # Return the first /dev/videoX after this line
            for j in range(i+1, len(lines)):
                if '/dev/video' in lines[j]:
                    return int(lines[j].strip().replace('/dev/video', ''))
    return -1

cam1_idx = find_camera_index('usb-1.4')
cam2_idx = find_camera_index('usb-1.2')
cam3_idx = find_camera_index('usb-1.3')
print(f"cam1_idx: {cam1_idx}, cam2_idx: {cam2_idx}, cam3_idx: {cam3_idx}")

# Initialize camera captures (3 cameras) and set frame buffer to 1 to always get the freshest frame
video_cam1 = cv2.VideoCapture(cam1_idx, cv2.CAP_V4L2) if cam1_idx != -1 else None
if video_cam1 is not None:
    video_cam1.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    video_cam1.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
    video_cam1.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    video_cam1.set(cv2.CAP_PROP_FRAME_HEIGHT, 360)

video_cam2 = cv2.VideoCapture(cam2_idx, cv2.CAP_V4L2) if cam2_idx != -1 else None
if video_cam2 is not None:
    video_cam2.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    video_cam2.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'YUYV'))
    video_cam2.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
    video_cam2.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)

video_cam3 = cv2.VideoCapture(cam3_idx, cv2.CAP_V4L2) if cam3_idx != -1 else None
if video_cam3 is not None:
    video_cam3.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    video_cam3.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'YUYV'))
    video_cam3.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
    video_cam3.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
new_width = 640
new_height = 480
newestframe = None   # Latest frame from cam1, updated by frame_task thread
newestframe2 = None  # Latest frame from cam2, updated by frame_task thread
newestframe3 = None  # Latest frame from cam3, updated by frame_task thread

# Initialize ADS1015 ADC (I2C address 0x48) and map analog channels to sensors
ads = ADS1015(i2c_bus, address=0x48)
m1 = AnalogIn(ads, ads1x15.Pin.A0)   # Soil moisture sensor
tds = AnalogIn(ads, ads1x15.Pin.A2)  # TDS (total dissolved solids) sensor
pH = AnalogIn(ads, ads1x15.Pin.A3)   # pH sensor

# Calibration bounds for moisture sensor voltage -> percentage conversion
maxm1 = 1.2558  # Voltage reading in air (dry)
minm1 = 0.16073 # Voltage reading submerged (wet)

# Moisture sensor % reading for watering logic
moist1 = 0

# Variables to hold that last gained sensor value for safety
lasthumid = None
lasttemp = None
lastvoc = None
lastmoist = 0
lasttds = 0
lastph = 0

# Lock to prevent concurrent I2C access across threads
i2c_lock = threading.Lock()

# --- State Variables ---
manualphoto = False       # Flag to trigger a one-off manual photo
previous = time.time()    # Timestamp of last photo
delta = 0                 # Time elapsed since last photo (seconds)
istest = False            # Whether a test sequence is currently running
reference = 1             # Reserved for future use
startingphoto = True      # Forces an immediate photo on first run
photolistlocation = "TC-HUNCH-Nanolab/webpages/" + module_config + "/photos/photolist.json"
monitoring_photos_location = "/home/nanolab/TC-HUNCH-Nanolab/webpages/" + module_config + "/photos"
testtime = None           # Timestamp folder name for current test session
olddelta = None           # Saved delta to restore after a test completes
newphoto = False          # Flag indicating a new photo was just saved and needs logging
test_constant = 2.98 # Base pump run duration in seconds PLUS OFFSET (2.20+0.78)
newfilelist = []          # List to manage the new files that must be added to the json
stopper = False           # Stops photo capture when test photo count is reached

# Initialize pump control pin (GPIO D20) as digital output, starts OFF
pump_pin = digitalio.DigitalInOut(board.D20)
pump_pin.direction = digitalio.Direction.OUTPUT
pump_pin.value = False

testcheck = ""            # Tracks which page triggered the test, used to coordinate threads
testfirstrun = False      # Ensures test initialization only happens once per test
testphotocount = 0        # Counter for photos taken in the current test
pump_modifyer = 1         # Multiplier applied to test_constant for variable pump durations

avg_wet = 0               # Smoothed AI result: 0 = dry, 1 = wet
aiword = ""               # Human-readable version of avg_wet ("Dry" or "Wet")
pumpcooldown = False      # Auto-Pumping Cooldown to prevent overpumping
pumpingstarttime = 0      # Auto-Pumping timing variable to manage pumpinmg interval - initialized to 0 before first water
# --- Functions ---

def obtain_frame():
    """Read a single frame from cam1. Returns None if capture fails."""
    ret, frame = video_cam1.read()
    if frame is None or ret is False:
        time.sleep(0.1)
    else:
        return frame

def obtain_frame2():
    """Read a single frame from cam2. Returns None if capture fails."""
    ret, frame = video_cam2.read()
    if frame is None or ret is False:
        time.sleep(0.1)
    else:
        return frame
    
def obtain_frame3():
    """Read a single frame from cam3. Returns None if capture fails."""
    ret, frame = video_cam3.read()
    if frame is None or ret is False:
        time.sleep(0.1)
    else:
        return frame

def root_ai_read():
    """
    Run the TFLite model on the latest cam1 frame to classify root zone
    as wet or dry. Updates the rolling average prediction (avg_wet).
    """
    global avg_wet
    
    if newestframe is None:
        return
    
    frame = newestframe.copy()

    # Preprocess: resize to model input size, convert to grayscale, normalize to [0, 1]
    frame_proc = cv2.resize(frame, (w, h))
    frame_proc = cv2.cvtColor(frame_proc, cv2.COLOR_BGR2GRAY)
    frame_proc = frame_proc.astype(np.float32) / 255.0
    frame_proc = np.expand_dims(frame_proc, axis=-1)  # Add channel dimension
    frame_proc = np.expand_dims(frame_proc, axis=0)   # Add batch dimension

    # Run inference
    interpreter.set_tensor(input_details[0]['index'], frame_proc)
    interpreter.invoke()
    output = interpreter.get_tensor(output_details[0]['index'])[0][0]

    # Threshold output to binary wet/dry classification
    wet = 1 if output > 0.5 else 0

    # Update rolling window and compute smoothed average
    predictions.append(wet)
    avg_wet = round(sum(predictions) / len(predictions))

    # Occasionally print the result to avoid flooding the console
    print_prob = random.randint(1, 7000)
    if print_prob == 7:
        print(avg_wet)

@app.after_request
def disable_cache(response):
    """Prevent browsers from caching responses so sensor data and images stay fresh."""
    response.headers['Cache-Control'] = 'no-store'
    return response

def pump_cycle(modifyer):
    """
    Run the pump for (test_constant * modifyer) seconds.
    Prints remaining time every 0.25s while active.
    """
    global test_constant, pump_pin, istest
    pump_time = test_constant * modifyer
    current = time.time()
    end = current + pump_time
    pump_pin.value = True
    while time.time() <= end:
        print("Pumping! Time left= " + str(end - time.time()))
        time.sleep(0.25)
    pump_pin.value = False

def get_time_information():
    """Return a formatted time string (e.g. '4:17:39 PM') for chart labels and JSON records."""
    if int(datetime.now().hour) >= 12:
        amorpm = "pm"
    else:
        amorpm = "am"
    formatted_time = str(datetime.now().time())[:7] + " " + amorpm
    return formatted_time

@app.route('/sensor_data')
def sensor_data():
    """
    Flask endpoint that reads all sensors and returns a JSON payload.
    Falls back to last known values if a sensor read fails.
    """
    global aiword, avg_wet, lasthumid, lasttemp, lastvoc, lastmoist, lasttds, lastph, moist1
    with i2c_lock:
        try:
            humidity = round(bme680.humidity, 1)
            lasthumid = humidity
        except Exception as e:
            if lasthumid is None:
                humidity = 0
            else:
                humidity = lasthumid
        try:
            temperature = round(bme680.temperature, 1)
            lasttemp = temperature
        except Exception as e:
            temperature = lasttemp
        try:
            voc = round(bme680.gas, 1) / 1000
            lastvoc = voc
        except Exception as e:
            voc = lastvoc

        # Convert moisture voltage to percentage using calibration bounds
        try:
            raw_moist = m1.voltage
            lastmoist = raw_moist
        except Exception:
            raw_moist = lastmoist
        try:
            tdsvolt = tds.voltage
            lasttds = tdsvolt
        except Exception:
            tdsvolt = lasttds
        try:
            ph = pH.voltage
            lastph = ph
        except Exception:
            ph = lastph

    moist1 = round(((raw_moist - maxm1) / (minm1 - maxm1)) * 100, 0)
    if moist1 >= 100:
        moist1 = 100
    if moist1 <= 0:
        moist1 = 0

    # Convert TDS voltage to ppm equivalent
    tdsraw = ((tdsvolt / 2.3) * 1000)
    TDS = int(round(tdsraw, 0))

    visionresult = avg_wet
    # Translate binary AI result to human-readable string
    if avg_wet == 0 or avg_wet == "0":
       aiword = "Dry"
    else:
       aiword = "Wet"
    return jsonify({'humidity': humidity, 'temperature': temperature, 'VOC': voc, 'AI': visionresult, 'aiword': aiword, 'moist1': moist1, 'pH': ph, 'tds': TDS})

def local_sensor_record():
    """
    Read all sensors and append a timestamped entry to today's JSON log file.
    Creates the file from scratch if it doesn't exist yet.
    """
    global aiword, avg_wet, lasthumid, lasttemp, lastvoc, lastmoist, lasttds, lastph
    with i2c_lock:
        try:
            humidity = round(bme680.humidity, 1)
            lasthumid = humidity
        except Exception as e:
            if lasthumid is None:
                humidity = 0
            else:
                humidity = lasthumid
        try:
            temperature = round(bme680.temperature, 1)
            lasttemp = temperature
        except Exception as e:
            temperature = lasttemp
        try:
            voc = round(bme680.gas, 1) / 1000
            lastvoc = voc
        except Exception as e:
            voc = lastvoc

        # Convert moisture voltage to percentage using calibration bounds
        try:
            raw_moist = m1.voltage
            lastmoist = raw_moist
        except Exception:
            raw_moist = lastmoist
        try:
            tdsvolt = tds.voltage
            lasttds = tdsvolt
        except Exception:
            tdsvolt = lasttds
        try:
            ph = pH.voltage
            lastph = ph
        except Exception:
            ph = lastph

    moist1 = round(((raw_moist - maxm1) / (minm1 - maxm1)) * 100, 0)
    if moist1 >= 100:
        moist1 = 100
    if moist1 <= 0:
        moist1 = 0

    # Convert TDS voltage to ppm equivalent
    tdsraw = ((tdsvolt / 2.3) * 1000)
    TDS = int(round(tdsraw, 0))

    ph = ph  # Raw pH voltage (calibration handled client-side or elsewhere)

    visionresult = avg_wet
    # Translate binary AI result to human-readable string
    if avg_wet == 0 or avg_wet == "0":
       aiword = "Dry"
    else:
       aiword = "Wet"

    # Use today's date as the JSON filename (e.g. "2026-04-28.json")
    day = str(datetime.now().date())
    try:
            with open("TC-HUNCH-Nanolab/" + day + ".json", 'r') as f:
                data = json.load(f)
            entry = {
                "Time" : get_time_information(),
                "Humidity" : str(humidity) + " %",
                "Temperature" : str(temperature) + " °C",
                "VOC" : str(voc) + " kΩ",
                "TDS" : str(TDS) + " %",
                "AI" : avg_wet,
            }
            data.append(entry)
            with open("TC-HUNCH-Nanolab/" + day + ".json", 'w') as f:
                    json.dump(data, f, indent=4)
    except FileNotFoundError:
        # Create day's .json from scratch if it doesn't exist yet
            data = []
            entry = {
                "Time" : get_time_information(),
                "Humidity" : str(humidity) + " %",
                "Temperature" : str(temperature) + " °C",
                "VOC" : str(voc) + " kΩ",
                "TDS" : str(TDS) + " %",
                "AI" : avg_wet,
            }
            data.append(entry)
            with open("TC-HUNCH-Nanolab/" + day + ".json", 'w') as f:
                    json.dump(data, f, indent=4)

def video_stream():
    """
    Generator that yields MJPEG frames from cam1 for the live video feed endpoint.
    Resizes and JPEG-encodes the latest frame on each iteration.
    """
    global newestframe
    while True:
         if newestframe is not None:  
            frame = newestframe.copy()
            resized_frame = cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_AREA)
            ret, buffer = cv2.imencode('.jpg', resized_frame)
            frame_bytes = buffer.tobytes()

            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            time.sleep(0.033)

def video_stream2():
    """
    Generator that yields MJPEG frames from cam2 for the live video feed endpoint.
    Resizes and JPEG-encodes the latest frame on each iteration.
    """
    global newestframe2
    while True:
         if newestframe2 is not None:        
            frame = newestframe2.copy()
            resized_frame = cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_AREA)
            ret, buffer = cv2.imencode('.jpg', resized_frame)
            frame_bytes = buffer.tobytes()

            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            time.sleep(0.033)

def video_stream3():
    """
    Generator that yields MJPEG frames from cam3 for the live video feed endpoint.
    Resizes and JPEG-encodes the latest frame on each iteration.
    """
    global newestframe3
    while True:
         if newestframe3 is not None:  
            frame = newestframe3.copy()
            resized_frame = cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_AREA)
            ret, buffer = cv2.imencode('.jpg', resized_frame)
            frame_bytes = buffer.tobytes()

            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            time.sleep(0.033)

@app.route('/video_feed_cam1')
def video_feed():
    """Streams live MJPEG video from cam1."""
    return Response(video_stream(), mimetype= 'multipart/x-mixed-replace; boundary=frame')

@app.route('/video_feed_cam2')
def video_feed2():
    """Streams live MJPEG video from cam2."""
    return Response(video_stream2(), mimetype= 'multipart/x-mixed-replace; boundary=frame')

@app.route('/video_feed_cam3')
def video_feed3():
    """Streams live MJPEG video from cam3."""
    return Response(video_stream3(), mimetype= 'multipart/x-mixed-replace; boundary=frame')

def save_all_cameras(folder, timestamp, prefix=""):
    """Capture and save the latest frame from each active camera to the given folder."""
    global newestframe, newestframe2, newestframe3, newphoto, newfilelist

    # CAM1
    if video_cam1 is not None and newestframe is not None:
        frame = newestframe.copy()
        resized = cv2.resize(frame, (new_width, new_height))
        name = f"{timestamp}_cam1.jpg"
        cv2.imwrite(folder + name, resized)
        newfilelist.append(prefix + "/" + f"{timestamp}_cam1.jpg")

    # CAM2
    if video_cam2 is not None and newestframe2 is not None:
        frame = newestframe2.copy()
        resized = cv2.resize(frame, (new_width, new_height))
        name = f"{timestamp}_cam2.jpg"
        cv2.imwrite(folder + name, resized)
        newfilelist.append(prefix + "/" + f"{timestamp}_cam2.jpg")

    # CAM3
    if video_cam3 is not None and newestframe3 is not None:
        frame = newestframe3.copy()
        resized = cv2.resize(frame, (new_width, new_height))
        name = f"{timestamp}_cam3.jpg"
        cv2.imwrite(folder + name, resized)
        newfilelist.append(prefix + "/" + f"{timestamp}_cam3.jpg")

    newphoto = True

@app.route('/', defaults={'path': 'index.html'})
@app.route('/<path:path>')
def serve_page(path):
    """Serve static files (HTML, CSS, JS) from the module's web directory."""
    return send_from_directory(WEB_DIR, path)

@app.route('/settings_form', methods=['POST'])
def settings_form():
    """
    Handle settings form submission. Updates config.txt and live sensor
    settings, then redirects to the dashboard.
    """
    ambient_pressure = request.form['ap']
    bme680.seaLevelhPa = float(ambient_pressure)
    module_config = request.form['config']
    bright = request.form['npb']
    testphotogap = request.form['ps']
    requestedphotocount = request.form['ppt']
    monitortime = request.form['pf']
    with open('config.txt', 'w') as file:
        file.write(str(ambient_pressure) + "\n")
        file.write(str(module_config) + "\n")
        file.write(str(bright) + "\n")
        file.write(str(testphotogap) + "\n")
        file.write(str(requestedphotocount) + "\n")
        file.write(str(monitortime) + "\n")
    return redirect(url_for('dashpage'))

@app.route('/dashboard')
def dashpage():
     return render_template('index.html')

@app.route('/takephoto')
def photopage():
     return render_template('photos.html')

@app.route('/graphpage')
def graphpage():
    return render_template('analytics.html')

@app.route('/controlbutton', methods=['POST'])
def controls():
    """
    Handle control panel button presses:
    - growmode: switches LEDs to red/blue grow light spectrum
    - viewmode: resets LEDs to warm white viewing light
    - manualphoto: triggers an immediate one-off photo
    - starttest: begins a timed pump + photo test sequence
    """
    global growmode, viewmode, manualphoto, istest, testcheck, delta, previous, testtime, stopper, testphotocount
    returnpage = 'dashpage'
    if 'growmode' in request.form:
         # Red LEDs for chlorophyll-a, blue LEDs for chlorophyll-b absorption
         pixels[2] = (255, 0, 0)
         pixels[6] = (255, 0, 0)
         pixels[3] = (0, 0, 255)
         pixels[7] = (0, 0, 255)
         pixels.show()
         returnpage = 'dashpage'
    if 'viewmode' in request.form:
         pixels.fill((255, 200, 180))  # Warm white for camera/visual inspection
         pixels.show()
         returnpage = 'dashpage'
    if 'manualphoto' in request.form:
         manualphoto = True
         returnpage = 'photopage'
    if 'starttest' in request.form:
         testtime = None
         stopper = False
         testphotocount = 0
         istest = True
         returnpage = 'graphpage'
         delta = 0                  # ← reset so the huge monitoring delta is gone
         previous = time.time()     # ← fresh start for the test timer
    testcheck = returnpage
    return redirect(url_for(returnpage))

def monitored_photos():
    """
    Background thread that handles all photo capture logic:
    - Periodic monitoring photos (taken every `monitortime` seconds)
    - Test sequence photos (rapid burst at `testphotogap` intervals)
    - Manual one-off photos
    - Updates photolist.json with paths to all saved photos
    """
    global previous, delta, istest, testtime, startingphoto, photolistlocation, manualphoto, olddelta, newphoto, newestframe, testfirstrun, stopper, testphotocount, testphotogap, monitortime, requestedphotocount, newfilelist
    while True:
        if istest == False:
                current = time.time()
                delta = current - previous
                if startingphoto == True:
                     delta = monitortime  # Force an immediate photo on first run
                     startingphoto = False
                dataset = "photos"
                currenttimeget = str(datetime.now())
                currenttime = currenttimeget.replace(" ", "at")  # Make timestamp filename-safe
                currenttime = currenttimeget.replace(":", "-")
                if delta >= monitortime:  # Take a photo once the monitoring interval has elapsed
                    save_all_cameras(monitoring_photos_location + "/", currenttime)
                    delta = 0
                    previous = current
                if olddelta is not None:
                    delta = olddelta  # Restore pre-test delta when returning to monitoring mode
                    olddelta = None

        if istest == True and stopper == False:
            if testtime is None:
                testtime = str(datetime.now()).replace(" ", "at").replace(":", "-")
            if testfirstrun == True:
                # Initialize test: save current delta, reset timer, create timestamped folder
                olddelta = delta
                delta = 0
                previous = time.time()
                testfirstrun = False
            test_folder = "/home/nanolab/TC-HUNCH-Nanolab/webpages/" + str(module_config) + "/photos/" + testtime
            os.makedirs(test_folder, exist_ok=True)
            dataset = "testphotos"
            current = time.time()
            delta = current - previous
            currenttimeget = str(datetime.now())
            currenttime = currenttimeget.replace(" ", "at")
            currenttime = currenttimeget.replace(":", "-")
            if delta >= testphotogap:
               save_all_cameras(test_folder + "/", currenttime, testtime)
               previous = current
               testphotocount = testphotocount + 1
               if testphotocount >= requestedphotocount:
                    stopper = True  # Stop capturing once target count is reached
               if delta >= test_constant:
                    istest = False  # Safety timeout: exit test mode if pump cycle time elapses without completion

        if manualphoto == True:
               currenttimeget = str(datetime.now())
               currenttime = currenttimeget.replace(" ", "at")  # Make timestamp filename-safe
               currenttime = currenttimeget.replace(":", "-")
               dataset = "photos"
               save_all_cameras(monitoring_photos_location + "/", currenttime)
               manualphoto = False

        if newphoto == True:
                # Append the new photo path to photolist.json for the web UI
                try:
                        with open(photolistlocation, 'r') as f:
                             data = json.load(f)
                        if dataset not in data:
                             data[dataset] = []
                        for photos in newfilelist:
                             data[dataset].append(photos)
                        with open(photolistlocation, 'w') as f:
                             json.dump(data, f, indent=4)
                except FileNotFoundError:
                        # Create photolist.json from scratch if it doesn't exist yet
                        with open('photolist.json', 'w') as f:
                             json.dump({dataset: newfilelist}, f, indent = 4)
                        shutil.move('/home/nanolab/photolist.json', photolistlocation)
                newphoto = False
                newfilelist = []

@app.route('/photolist.json')
def photo_json():
    """Serve the photo index JSON file to the frontend."""
    return send_from_directory("../webpages/" + module_config + "/photos/photolist.json")

@app.route('/photos/<path:filename>')
def photos(filename):
    """Serve individual photo files from the module's photos directory."""
    return send_from_directory("../webpages/" + module_config + "/photos", filename)

## --- Main Entry Point ---
if __name__ == "__main__":
        def background_sensor_task():
            """Continuously poll sensors and log to JSON every second in the background."""
            with app.app_context():
                while True:
                    local_sensor_record()
                    time.sleep(1)

        def background_photo_task():
            """Run the photo monitoring loop in the background."""
            with app.app_context():
                monitored_photos()

        def root_ai_task():
            """Continuously run AI inference on the latest cam1 frame."""
            while True:
                root_ai_read()
                time.sleep(0.25)

        def test_task():
            """
            Watch for a test trigger from the web UI. When detected,
            runs a pump cycle and resets test state for the next run.

            While not in a test setting, watch the moisture sensor and 
            AI vision model. If the plant needs watering, pump for 2.5
            seconds and then watch over for 5 seconds to let water travel.
            This cycle repeats as the plane is in need of water.
            """
            global pump_modifyer, testcheck, testfirstrun, testphotocount, testtime, pumpcooldown, pumpingstarttime, moist1
            while True:
                if testcheck == "graphpage":
                    testphotocount = 0
                    testfirstrun = True
                    pump_cycle(pump_modifyer)
                    testcheck = ""
                """else:
                     if avg_wet == 0 and moist1 >= 50 and pumpcooldown == False: #If the plant needs water and the plant is not currently in a cycle
                          pumpingstarttime = time.time() #Take a baseline time
                          while time.time() - pumpingstarttime <= 2.5: #For 2.5 seconds
                               pump_pin.value = True #Turn the pump on
                               time.sleep(0.5)
                          pump_pin.value = False #Turn the pump off
                          pumpcooldown = True #Start a cooldown to prevent race conditions while the water travels
                     if time.time() - pumpingstarttime >= 5: #End the cooldown after 5 Seconds
                         pumpcooldown = False
                         pumpingstarttime = 0"""
                time.sleep(0.25) 
               
        #Continuously grab the latest frame from all 3 cameras into shared variables.
        def frame_task():
            global newestframe
            while True:
                if video_cam1 is None:
                    time.sleep(0.05)
                else:
                    frame = obtain_frame()
                    if frame is not None and video_cam1.isOpened():
                        newestframe = frame
                        time.sleep(0.05)
                    else:
                        time.sleep(0.05)
        def frame_task2():
            global newestframe2
            while True:
                if video_cam2 is None:
                    time.sleep(0.05)
                else:
                    frame2 = obtain_frame2()
                    if frame2 is not None and video_cam2.isOpened():
                        newestframe2 = frame2
                        time.sleep(0.05)
                    else:
                        time.sleep(0.05)

        def frame_task3():
            global newestframe3
            while True:
                if video_cam3 is None:
                    time.sleep(0.05)
                else:
                    frame3 = obtain_frame3()
                    if frame3 is not None and video_cam3.isOpened():
                        newestframe3 = frame3
                        time.sleep(0.05)
                    else:
                        time.sleep(0.05)

        # Create and start all background threads
        sensor_thread = threading.Thread(target=background_sensor_task)
        photo_thread = threading.Thread(target=background_photo_task)
        root_ai_thread = threading.Thread(target=root_ai_task)
        test_thread = threading.Thread(target=test_task)
        frame_thread = threading.Thread(target=frame_task)
        frame_thread2 = threading.Thread(target=frame_task2)
        frame_thread3 = threading.Thread(target=frame_task3)

        frame_thread.start()   # Start camera capture first so other threads have frames to work with
        frame_thread2.start()
        frame_thread3.start()
        sensor_thread.start()
        photo_thread.start()
        root_ai_thread.start()
        test_thread.start()

        # Launch Flask web server (threaded=True allows concurrent requests)
        app.run(host="0.0.0.0", port=5000, use_reloader=False, threaded=True)
