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

MODEL = "Root_Classification_Model.tflite"
interpreter = Interpreter(model_path=MODEL)
interpreter.allocate_tensors()
input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()
_, h, w, c = input_details[0]['shape']
avg_window = 20
predictions = deque(maxlen=avg_window)

i2c_bus = board.I2C() ## Initialization of sensors
bme680 = adafruit_bme680.Adafruit_BME680_I2C(i2c_bus, address=0x77)
try:
     line1 = linecache.getline("/home/nanolab/config.txt", 1)
     ambient_pressure = float(line1)
except Exception as e:
     ambient_pressure = 1013
     print("Please Configure Settings")
bme680.seaLevelhPa = ambient_pressure

try:
     line2 = linecache.getline("/home/nanolab/config.txt", 2)
     module_config = str(line2)
     module_config = module_config.replace("\n", "")
except Exception as e:
     module_config = "aeroponictest"
     print("Please Configure Settings")

try:
     line3 = linecache.getline("/home/nanolab/config.txt", 3)
     bright = float(line3.strip())

except Exception as e:
     bright = 0.1
     print("Please Configure Settings")

pixelcount = 20
pixels = neopixel.NeoPixel(board.D18, pixelcount, brightness=bright, auto_write=False)

pixels.fill((255, 200, 180))
pixels.show()

try:
     line4 = linecache.getline("/home/nanolab/config.txt", 4)
     testphotogap = float(line4.strip())

except Exception as e:
     testphotogap = 0.5
     print("Please Configure Settings")

try:
     line5 = linecache.getline("/home/nanolab/config.txt", 5)
     requestedphotocount = float(line5.strip())

except Exception as e:
     requestedphotocount = 10
     print("Please Configure Settings")

try:
     line6 = linecache.getline("/home/nanolab/config.txt", 6)
     monitortime = float(line6.strip())
     monitortime = ((monitortime * 60) * 60)

except Exception as e:
     monitortime = 21600
     print("Please Configure Settings")

app = Flask(__name__, template_folder='../webpages/' + module_config.strip())

WEB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../webpages/" + module_config.strip())
WEB_DIR = os.path.abspath(WEB_DIR)

video = cv2.VideoCapture(0)
video.set(cv2.CAP_PROP_BUFFERSIZE, 1)
new_width = 640
new_height = 480
newestframe = None

#ads = ADS1115(i2c_bus, address=0x48)
#m1 = AnalogIn(ads, ads1x15.Pin.A0)
#m2 = AnalogIn(ads, ads1x15.Pin.A1)
#tds = AnalogIn(ads, ads1x15.Pin.A2)
#pH = AnalogIn(ads, ads1x15.Pin.A3)

maxm1 = 1.2558
maxm2 = 1.7690
minm1 = 0.16073
minm2 = 0.62334

RESTART = False
manualphoto = False
previous = time.time()
delta = 0
istest = False
reference = 1
startingphoto = True
photolistlocation = "TC-HUNCH-Nanolab/webpages/" + module_config + "/photos/photolist.json"
testtime = None
olddelta = None
newphoto = False
pump_constant = 5.18
stopper = False

pump_pin = digitalio.DigitalInOut(board.D20)
pump_pin.direction = digitalio.Direction.OUTPUT
pump_pin.value = False
testcheck = ""
testfirstrun = False
testphotocount = 0
pump_modifyer = 1

avg_wet = 0
aiword = ""

#Functions
def obtain_frame():
    ret, frame = video.read()
    if frame is None or ret is False:
        time.sleep(0.1)
    else:
        return frame

def root_ai_read():
    global avg_wet
    
    if newestframe is None:
        return
    
    frame = newestframe.copy()
    frame_proc = cv2.resize(frame, (w, h))
    frame_proc = cv2.cvtColor(frame_proc, cv2.COLOR_BGR2GRAY)
    frame_proc = frame_proc.astype(np.float32) / 255.0
    frame_proc = np.expand_dims(frame_proc, axis=-1)  # channel dim
    frame_proc = np.expand_dims(frame_proc, axis=0)   # batch dim

    # Run TFLite inference
    interpreter.set_tensor(input_details[0]['index'], frame_proc)
    interpreter.invoke()
    output = interpreter.get_tensor(output_details[0]['index'])[0][0]

    # Convert to binary 0/1
    wet = 1 if output > 0.5 else 0

    # Add to deque and compute average
    predictions.append(wet)
    avg_wet = round(sum(predictions) / len(predictions))

    print_prob = random.randint(1, 7000)
    if print_prob == 7:
        print(avg_wet)

@app.after_request
def disable_cache(response):
    response.headers['Cache-Control'] = 'no-store'
    return response

def pump_cycle(modifyer):
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
    #moist1 = round(((m1.voltage - maxm1) / (minm1 - maxm1)) * 100, 0)
    #if moist1 >= 100:
        #moist1 = 100
    #if moist1 <= 0:
        #moist1 = 0
    #moist2 = round(((m2.voltage - maxm2) / (minm2 - maxm2)) * 100, 0)
    #if moist2 >= 100:
        #moist2 = 100
    #if moist2 <= 0:
        #moist2 = 0
    #tdsvolt = tds.voltage
    #tdsraw = ((tdsvolt / 2.3) * 1000)
    #TDS = int(round(tdsraw, 0))
    #ph = pH.voltage
    visionresult = avg_wet
    if avg_wet == 0 or avg_wet == "0":
       aiword = "Dry"
    else:
       aiword = "Wet"
    #return jsonify({'humidity': humidity, 'temperature': temperature, 'VOC': voc, 'moist1': moist1, 'moist2': moist2, 'tds': TDS})
    return jsonify({'humidity': humidity, 'temperature': temperature, 'VOC': voc, 'AI': visionresult, 'aiword': aiword})
    #return jsonify({'moist1': moist1, 'moist2': moist2, 'tds': TDS, 'pH': ph})

def video_stream():
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
    return Response(video_stream(), mimetype= 'multipart/x-mixed-replace; boundary=frame')

@app.route('/', defaults={'path': 'index.html'})
@app.route('/<path:path>')
def serve_page(path):
    return send_from_directory(WEB_DIR, path)

@app.route('/settings_form', methods=['POST'])
def settings_form():
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
     global growmode, viewmode, manualphoto, istest, testcheck, RESTART
     if 'growmode' in request.form:
         pixels[1] = (255, 0, 0)
         pixels[4] = (255, 0, 0)
         pixels[7] = (255, 0, 0)

         pixels[2] = (0, 0, 255)
         pixels[8] = (0, 0, 255)
         pixels[10] = (0, 0, 255)
         pixels.show()

         returnpage = 'dashpage'
     if 'viewmode' in request.form:
         pixels.fill((255, 200, 180))
         pixels.show()
         returnpage = 'dashpage'
     if 'manualphoto' in request.form:
         manualphoto = True
         returnpage = 'photopage'
     if 'starttest' in request.form:
         istest = True
         returnpage = 'graphpage'
     if 'restart' in request.form:
         RESTART = True
         video.release()
         subprocess.Popen(
             [sys.executable] + sys.argv,
             cwd=os.getcwd(),
             env=os.environ.copy(),
             stdout=sys.stdout,
             stderr=sys.stderr
         ) 
         os._exit(0)
     testcheck = returnpage
     return redirect(url_for(returnpage))

def monitored_photos():
    global previous, delta, istest, testtime, startingphoto, photolistlocation, manualphoto, olddelta, newphoto, newestframe, testfirstrun, stopper, testphotocount, testphotogap, monitortime, requestedphotocount
    while True:
        if istest == False:
                current = time.time()
                delta = current - previous
                if startingphoto == True:
                     delta = monitortime
                     startingphoto = False
                dataset = "photos"
                currenttimeget = str(datetime.now())
                currenttime = currenttimeget.replace(" ", "at")
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
                    delta = olddelta
                    olddelta = None
        if istest == True and stopper == False:
            if testfirstrun == True:
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
                    stopper = True
            if delta >= 5.18:
                istest = False
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

@app.route('/photolist.json')
def photo_json():
	return send_from_directory("../webpages/" + module_config + "/photos/photolist.json")

@app.route('/photos/<path:filename>')
def photos(filename):
	return send_from_directory("../webpages/" + module_config + "/photos", filename)

##Procedural
if __name__ == "__main__":
        def background_sensor_task():
           with app.app_context():
            while True:
                sensor_data()
                time.sleep(2)
        def background_photo_task():
           with app.app_context():
                monitored_photos()
        def root_ai_task():
            while True:
                if RESTART is not True:
                    root_ai_read()
        def test_task():
            global pump_modifyer, testcheck, testfirstrun, testphotocount, testtime
            while True:
                if testcheck == "graphpage":
                    testfirstrun = True
                    pump_cycle(pump_modifyer)
                    testcheck = ""
                    testtime = None
                    testphotocount = 0
        def frame_task():
            global newestframe
            while True:
                if RESTART == True:
                    return None
                frame = obtain_frame()
                if frame is not None:
                    newestframe = frame
                else:
                    time.sleep(0.02)
        sensor_thread = threading.Thread(target=background_sensor_task)
        photo_thread = threading.Thread(target=background_photo_task)
        root_ai_thread = threading.Thread(target=root_ai_task)
        test_thread = threading.Thread(target=test_task)
        frame_thread = threading.Thread(target=frame_task)
        frame_thread.start()
        sensor_thread.start()
        photo_thread.start()
        root_ai_thread.start()
        test_thread.start()
        app.run(host="0.0.0.0", port=5000, use_reloader=False, threaded=True)
