##Setup
import digitalio
import board
import os
import adafruit_bme680
from adafruit_ads1x15 import ADS1115, AnalogIn, ads1x15
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
pixelcount = 20
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
     requestedphotocount = float(line5.strip())
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

# Initialize camera capture and set frame buffer to 1 to always get the freshest frame
video = cv2.VideoCapture(0)
video.set(cv2.CAP_PROP_BUFFERSIZE, 1)
new_width = 640
new_height = 480
newestframe = None  # Shared variable updated by the frame capture thread

# Initialize ADS1115 ADC (I2C address 0x48) and map analog channels to sensors
ads = ADS1115(i2c_bus, address=0x48)
m1 = AnalogIn(ads, ads1x15.Pin.A0)   # Soil moisture sensor
tds = AnalogIn(ads, ads1x15.Pin.A2)  # TDS (total dissolved solids) sensor
pH = AnalogIn(ads, ads1x15.Pin.A3)   # pH sensor

# Calibration bounds for moisture sensor voltage -> percentage conversion
maxm1 = 1.2558  # Voltage reading in air (dry)
minm1 = 0.16073 # Voltage reading submerged (wet)

# --- State Variables ---
manualphoto = False       # Flag to trigger a one-off manual photo
previous = time.time()    # Timestamp of last photo
delta = 0                 # Time elapsed since last photo
istest = False            # Whether a test sequence is currently running
reference = 1
startingphoto = True      # Forces an immediate photo on first run
photolistlocation = "TC-HUNCH-Nanolab/webpages/" + module_config + "/photos/photolist.json"
testtime = None           # Timestamp folder name for current test session
olddelta = None           # Saved delta to restore after a test
newphoto = False          # Flag indicating a new photo was just saved
pump_constant = 5.18      # Base pump run duration in seconds
stopper = False           # Stops photo capture when test photo count is reached

# Initialize pump control pin (GPIO D20) as digital output, starts OFF
pump_pin = digitalio.DigitalInOut(board.D20)
pump_pin.direction = digitalio.Direction.OUTPUT
pump_pin.value = False

testcheck = ""            # Tracks which page triggered the test, used to coordinate threads
testfirstrun = False      # Ensures test initialization only happens once per test
testphotocount = 0        # Counter for photos taken in the current test
pump_modifyer = 1         # Multiplier applied to pump_constant for variable pump durations

avg_wet = 0               # Rolling average AI result: 0 = dry, 1 = wet
aiword = ""               # Human-readable version of avg_wet ("Dry" or "Wet")

# --- Functions ---

def obtain_frame():
    """Read a single frame from the camera. Returns None if capture fails."""
    ret, frame = video.read()
    if frame is None or ret is False:
        time.sleep(0.1)
    else:
        return frame

def root_ai_read():
    """
    Run the TFLite model on the latest camera frame to classify root zone
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
    Run the pump for (pump_constant * modifyer) seconds.
    Prints remaining time every 0.25s while active.
    """
    global pump_constant, pump_pin, istest
    pump_time = pump_constant * modifyer
    current = time.time()
    end = current + pump_time
    pump_pin.value = True
    while time.time() <= end:
        print("Pumping! Time left= " + str(end - time.time()))
        time.sleep(0.25)
    pump_pin.value = False

@app.route('/sensor_data')
def sensor_data():
    """
    Flask endpoint that reads all sensors and returns a JSON payload.
    Falls back to last known values if a sensor read fails.
    """
    global aiword, avg_wet
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
        lasttemp = temperature
    try:
        voc = round(bme680.gas, 1) / 1000
        lastvoc = voc
    except Exception as e:
        voc = lastvoc

    # Convert moisture voltage to percentage using calibration bounds
    moist1 = round(((m1.voltage - maxm1) / (minm1 - maxm1)) * 100, 0)
    if moist1 >= 100:
        moist1 = 100
    if moist1 <= 0:
        moist1 = 0

    # Convert TDS voltage to ppm
    tdsvolt = tds.voltage
    tdsraw = ((tdsvolt / 2.3) * 1000)
    TDS = int(round(tdsraw, 0))

    ph = pH.voltage  # Raw pH voltage (calibration handled client-side or elsewhere)

    visionresult = avg_wet
    # Translate binary AI result to human-readable string
    if avg_wet == 0 or avg_wet == "0":
       aiword = "Dry"
    else:
       aiword = "Wet"
    return jsonify({'humidity': humidity, 'temperature': temperature, 'VOC': voc, 'AI': visionresult, 'aiword': aiword, 'moist1': moist1, 'pH': ph, 'tds': TDS})

def video_stream():
    """
    Generator that yields MJPEG frames for the live video feed endpoint.
    Resizes and JPEG-encodes the latest frame on each iteration.
    """
    global newestframe
    while True:
            frame = newestframe.copy()
            resized_frame = cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_AREA)
            ret, buffer = cv2.imencode('.jpg', resized_frame)
            frame_bytes = buffer.tobytes()

            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

@app.route('/video_feed')
def video_feed():
    """Streams live MJPEG video from the camera."""
    return Response(video_stream(), mimetype= 'multipart/x-mixed-replace; boundary=frame')

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
     global growmode, viewmode, manualphoto, istest, testcheck
     if 'growmode' in request.form:
         # Red LEDs for chlorophyll-a, blue LEDs for chlorophyll-b absorption
         pixels[1] = (255, 0, 0)
         pixels[4] = (255, 0, 0)
         pixels[7] = (255, 0, 0)
         pixels[2] = (0, 0, 255)
         pixels[8] = (0, 0, 255)
         pixels[10] = (0, 0, 255)
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
         istest = True
         returnpage = 'graphpage'
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
    global previous, delta, istest, testtime, startingphoto, photolistlocation, manualphoto, olddelta, newphoto, newestframe, testfirstrun, stopper, testphotocount, testphotogap, monitortime, requestedphotocount
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
                if delta >= monitortime:
                    if newestframe is None:
                        time.sleep(0.01)
                        continue
                    frame = newestframe.copy()
                    resized_frame = cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_AREA)
                    cv2.imwrite(currenttime + '.jpg', resized_frame)
                    folder = "/home/nanolab/TC-HUNCH-Nanolab/webpages/" + module_config + "/photos/"
                    shutil.move(currenttime + '.jpg', folder + currenttime + '.jpg')
                    delta = 0
                    newphoto = True
                    previous = current
                    photolocation = 'photos/' + str(currenttime) + '.jpg'
                    if testtime is not None:
                             testtime = None
                if olddelta is not None:
                    delta = olddelta  # Restore pre-test delta when returning to monitoring mode
                    olddelta = None

        if istest == True and stopper == False:
            if testfirstrun == True:
                # Initialize test: save current delta, reset timer, create timestamped folder
                olddelta = delta
                delta = 0
                stopper = False
                previous = time.time()
                testtime = str(datetime.now())
                testtime = testtime.replace(" ", "at")
                testfirstrun = False
            folder2 = "/home/nanolab/TC-HUNCH-Nanolab/webpages/" + str(module_config) + "/photos/" + testtime
            os.makedirs(folder2, exist_ok=True)
            dataset = "testphotos"
            current = time.time()
            delta = current - previous
            currenttimeget = str(datetime.now())
            currenttime = currenttimeget.replace(" ", "at")
            if delta >= testphotogap:
                if newestframe is None:
                    time.sleep(0.01)
                    continue
                frame = newestframe.copy()
                resized_frame = cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_AREA)
                cv2.imwrite(currenttime + '.jpg', resized_frame)
                folder = folder2
                shutil.move(currenttime + '.jpg', folder + '/' + currenttime + '.jpg')
                delta = 0
                newphoto = True
                previous = current
                photolocation = 'photos/' + str(testtime) + '/' + str(currenttime) + '.jpg'
                testphotocount = testphotocount + 1
                print("Photos Taken! " + str(testphotocount))
                if testphotocount == requestedphotocount:
                    stopper = True  # Stop capturing once target count is reached
            if delta >= 5.18:
                istest = False  # Safety timeout: exit test mode if pump cycle time elapses

        if manualphoto == True:
            # Reset photo timing so next scheduled photo captures immediately
            olddelta = delta
            startingphoto = True
            manualphoto = False

        if newphoto == True:
                # Append the new photo path to photolist.json for the web UI
                try:
                        with open(photolistlocation, 'r') as f:
                             data = json.load(f)
                        if dataset not in data:
                             data[dataset] = []
                        data[dataset].append(photolocation)
                        with open(photolistlocation, 'w') as f:
                             json.dump(data, f, indent=4)
                except FileNotFoundError:
                        # Create photolist.json from scratch if it doesn't exist yet
                        with open('photolist.json', 'w') as f:
                             json.dump({dataset: [photolocation]}, f, indent = 4)
                        shutil.move('/home/nanolab/photolist.json', photolistlocation)
                newphoto = False

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
            """Continuously poll sensors every 2 seconds in the background."""
            with app.app_context():
                while True:
                    sensor_data()
                    time.sleep(2)

        def background_photo_task():
            """Run the photo monitoring loop in the background."""
            with app.app_context():
                monitored_photos()

        def root_ai_task():
            """Continuously run AI inference on the latest camera frame."""
            while True:
                root_ai_read()

        def test_task():
            """
            Watch for a test trigger from the web UI. When detected,
            runs a pump cycle and resets test state for a fresh run.
            """
            global pump_modifyer, testcheck, testfirstrun, testphotocount, testtime
            while True:
                if testcheck == "graphpage":
                    testfirstrun = True
                    pump_cycle(pump_modifyer)
                    testcheck = ""
                    testtime = None
                    testphotocount = 0

        def frame_task():
            """Continuously grab the latest camera frame into the shared newestframe variable."""
            global newestframe
            while True:
                frame = obtain_frame()
                if frame is not None:
                    newestframe = frame
                else:
                    time.sleep(0.02)

        # Create and start all background threads
        sensor_thread = threading.Thread(target=background_sensor_task)
        photo_thread = threading.Thread(target=background_photo_task)
        root_ai_thread = threading.Thread(target=root_ai_task)
        test_thread = threading.Thread(target=test_task)
        frame_thread = threading.Thread(target=frame_task)

        frame_thread.start()   # Start camera capture first so other threads have frames to work with
        sensor_thread.start()
        photo_thread.start()
        root_ai_thread.start()
        test_thread.start()

        # Launch Flask web server (threaded=True allows concurrent requests)
        app.run(host="0.0.0.0", port=5000, use_reloader=False, threaded=True)
