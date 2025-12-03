import adafruit_bme680
from adafruit_ads1x15 import ADS1115, AnalogIn, ads1x15
import cv2
import neopixel

import digitalio
import board
import os

import time
from datetime import datetime
from flask import Flask, Response, jsonify, send_from_directory, request, render_template, redirect, url_for
import threading
import linecache
import shutil
import json

WEB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../webpages")
WEB_DIR = os.path.abspath(WEB_DIR)

app = Flask(__name__, template_folder='../webpages')
'''
time.sleep(1)
i2c_bus = board.I2C() ## Initialization of sensors
bme680 = adafruit_bme680.Adafruit_BME680_I2C(i2c_bus, address=0x77)
try:
     line = linecache.getline("config.txt", 1)
     ambient_pressure = line
except Exception as e:
     ambient_pressure = 1013
     print("Please Configure Settings")
bme680.seaLevelhPa = ambient_pressure

ads = ADS1115(i2c_bus, address=0x48)
m1 = AnalogIn(ads, ads1x15.Pin.A0)
m2 = AnalogIn(ads, ads1x15.Pin.A1)
tds = AnalogIn(ads, ads1x15.Pin.A2)
ph = AnalogIn(ads, ads1x15.Pin.A3)
'''
maxm1 = 1.2558
maxm2 = 1.7690
minm1 = 0.16073
minm2 = 0.62334

pumppin = digitalio.DigitalInOut(board.D1)
ledpin = board.D2
pixelcount = 20
bright = 0.3
pixels = neopixel.NeoPixel(ledpin, pixelcount, brightness=bright, auto_write=False)
'''
@app.route('/sensor_data')
def sensor_data():
    humidity = round(bme680.humidity, 1)
    temperature = round(bme680.temperature, 1)
    try:
     voc = round(bme680.gas, 1) / 1000
     lastvoc = voc
    except Exception as e:
     voc = lastvoc
    moist1 = round(((m1.voltage - maxm1) / (minm1 - maxm1)) * 100, 0)
    if moist1 >= 100:
        moist1 = 100
    if moist1 <= 0:
        moist1 = 0
    moist2 = round(((m2.voltage - maxm2) / (minm2 - maxm2)) * 100, 0)
    if moist2 >= 100:
        moist2 = 100
    if moist2 <= 0:
        moist2 = 0
    tdsvolt = tds.voltage
    tdsraw = ((tdsvolt / 2.3) * 1000)
    TDS = int(round(tdsraw, 0))
    return jsonify({'humidity': humidity, 'temperature': temperature, 'VOC': voc, 'moist1': moist1, 'moist2': moist2, 'tds': TDS})
'''
video = cv2.VideoCapture(0)
new_width = 640
new_height = 480
newestframe = None

def video_stream():
    while(True):
        ret, frame = video.read()
        if not ret:
            break
        else:
            resized_frame = cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_AREA)
            ret, buffer = cv2.imencode('.jpg', resized_frame)
            newestframe = ret, buffer
            frame_bytes = buffer.tobytes()

            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

@app.route('/video_feed')
def video_feed():
    return Response(video_stream(), mimetype= 'multipart/x-mixed-replace; boundary=frame')

@app.route('/', defaults={'path': 'index.html'})
@app.route('/<path:path>')
def serve_page(path):
    return send_from_directory(WEB_DIR, path)
'''
@app.route('/settings_form', methods=['POST'])
def settings_form():
    ambient_pressure = request.form['ap']
    bme680.seaLevelhPa = ambient_pressure

    ambient_temp = request.form['at']
    target_humidity = request.form['th']
    with open('config.txt', 'w') as file:
        file.write(str(ambient_pressure) + "\n")
        file.write(str(ambient_temp) + "\n")
        file.write(str(target_humidity) + "\n")
    return f"Preferences Set!"
'''
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
     global growmode, viewmode, manualphoto, istest, reference
     if 'growmode' in request.form:
         growmode = True
         returnpage = 'dashpage'
     if 'viewmode' in request.form:
         viewmode = True
         returnpage = 'dashpage'
     if 'manualphoto' in request.form:
         manualphoto = True
         returnpage = 'photopage'
     if 'starttest' in request.form:
         istest = "1"
         reference = time.time()
         returnpage = 'graphpage'
     return redirect(url_for(returnpage))

manualphoto = False
previous = time.time()
delta = 0
istest = "0"
reference = 1
startingphoto = True
photolistlocation = "TC-HUNCH-Nanolab/webpages/photos/photolist.json"
testtime = None
olddelta = None

def monitored_photos():
    global previous, delta, istest, testtime, startingphoto, photolistlocation, manualphoto, olddelta
    while True:
        if istest == "0":
                current = time.time()
                delta = current - previous
                if startingphoto == True:
                     delta = 21600
                     startingphoto = False
                dataset = "photos"
                currenttimeget = str(datetime.now())
                currenttime = currenttimeget.replace(" ", "at")
                if delta >= 21600:
                    ret, frame = video.read()
                    if not ret:
                        break
                    else:
                        resized_frame = cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_AREA)
                        cv2.imwrite(currenttime + '.jpg', resized_frame)
                        folder = '/home/nanolab/TC-HUNCH-Nanolab/webpages/photos/'
                        shutil.move(currenttime + '.jpg', folder + currenttime + '.jpg')
                        delta = 0
                        newphoto = True
                        previous = current
                        photolocation = 'photos/' + str(currenttime) + '.jpg'
                        if testtime is not None:
                             testtime = None
                if olddelta is not None:
                        delta = olddelta
                        olddelta = None
        if istest == "1":
                if testtime is None:
                      testtime = datetime.now()
                      folder2 = "/TC-HUNCH-Nanolab/webpages/photos/" + str(testtime)
                dataset = "testphotos"
                currenttimeget = str(datetime.now())
                currenttime = currenttimeget.replace(" ", "at")
                current = time.time()
                delta = current - previous

                if delta >= 1:
                    ret, frame = video.read()
                    if not ret:
                        break
                    else:
                        resized_frame = cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_AREA)
                        cv2.imwrite(currenttime + '.jpg', resized_frame)
                        shutil.move(currenttime + '.jpg', folder2 + currenttime + '.jpg')
                        previous = current
                        delta = 0
                        photolocation = 'photos/' + str(testtime) + '/' + str(currenttime) + '.jpg'
                        newphoto = True
        if manualphoto == True:
            olddelta = delta
            startingphoto = True
            manualphoto = False
        if newphoto == True:
                try:
                        with open(photolistlocation, 'r') as f:
                             data = json.load(f)
                        if dataset not in data:
                             data[dataset] = []
                        data[dataset].append(photolocation)
                        with open(photolistlocation, 'w') as f:
                             json.dump(data, f, indent=4)
                except FileNotFoundError:
                        with open('photolist.json', 'w') as f:
                             json.dump({dataset: [photolocation]}, f, indent = 4)
                        shutil.move('/home/nanolab/photolist.json', photolistlocation)
                newphoto = False
        if istest == 1:
                timer = time.time()
                if timer - reference == 5:
                     istest = "0"

@app.route('/photolist.json')
def photo_json():
	return send_from_directory("../webpages", "photolist.json")

@app.route('/photos/<path:filename>')
def photos(filename):
	return send_from_directory("../webpages/photos", filename)

if __name__ == "__main__":
    #    def background_sensor_task():
     #      with app.app_context():
      #      while True:
        #        sensor_data()
       #         time.sleep(2)
        def background_photo_task():
           with app.app_context():
            while True:
                monitored_photos()
   #     sensor_thread = threading.Thread(target=background_sensor_task)
        photo_thread = threading.Thread(target=background_photo_task)
   #     sensor_thread.daemon = True
        photo_thread.daemon = True
   #     sensor_thread.start()
        photo_thread.start()
        app.run(host="0.0.0.0", port=5000, debug=False)
