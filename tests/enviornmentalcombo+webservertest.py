import adafruit_bme680
from adafruit_ads1x15 import ADS1115, AnalogIn, ads1x15
import cv2

import digitalio
import board
import os

import time
from flask import Flask, Response, jsonify, send_from_directory, request, render_template
import threading
import subprocess
import linecache

WEB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../webpages")
WEB_DIR = os.path.abspath(WEB_DIR)

app = Flask(__name__)

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

maxm1 = 1.2558 
maxm2 = 1.7690 
minm1 = 0.16073 
minm2 = 0.62334

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
    return jsonify({'humidity': humidity, 'temperature': temperature, 'VOC': voc, 'moist1': moist1, 'moist2': moist2, 'tds': TD>

video = cv2.VideoCapture(0)
new_width = 640
new_height = 480

def video_stream():
    while(True):
        ret, frame = video.read()
        if not ret:
            break
        else:
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
    bme680.seaLevelhPa = ambient_pressure

    ambient_temp = request.form['at']
    target_humidity = request.form['th']
    with open('config.txt', 'w') as file:
        file.write(str(ambient_pressure) + "\n")
        file.write(str(ambient_temp) + "\n")
        file.write(str(target_humidity) + "\n")
    return f"Preferences Set!"

if __name__ == "__main__":
        def background_sensor_task():
           with app.app_context():
            while True:
                sensor_data()
                time.sleep(2)
        sensor_thread = threading.Thread(target=background_sensor_task)
        sensor_thread.daemon = True
        sensor_thread.start()
        app.run(host="0.0.0.0", port=5000)
