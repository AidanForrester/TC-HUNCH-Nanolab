import adafruit_bme680
from adafruit_ads1x15 import ADS1115, AnalogIn, ads1x15
import digitalio
import board
import os
import time
from flask import Flask, Response, jsonify, send_from_directory
import threading
import subprocess
WEB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "TC-HUNCH-Nanolab/webpages")

app = Flask(__name__)

time.sleep(1)
i2c_bus = board.I2C() ## Initialization of sensors
bme680 = adafruit_bme680.Adafruit_BME680_I2C(i2c_bus)
bme680.seaLevelhPa = 1013.25

ads = ADS1115(i2c_bus)
m1 = AnalogIn(ads, ads1x15.Pin.A0)
m2 = AnalogIn(ads, ads1x15.Pin.A1)

maxm1 = 2.0 ##TEST AND CHANGE THESE
maxm2 = 1.5 ##TEST AND CHANGE THESE
minm1 = .75 ##TEST AND CHANGE THESE
minm2 = .30 ##TEST AND CHANGE THESE

@app.route('/sensor_data')
def sensor_data():
    humidity = round(bme680.humidity, 1)
    temperature = round(bme680.temperature, 1)
    voc = round(bme680.gas, 1)
    moist1 = round(((m1.voltage - minm1) / maxm1) * 100), 1)
    moist1 = round(((m2.voltage - minm2) / maxm2) * 100), 1)
    return jsonify({'humidity': humidity, 'temperature': temperature, 'gas': gas, 'moist1': moist1, 'moist2'})

@app.route('/', defaults={'path': 'index.html'})
@app.route('/<path:path>')
def serve_page(path):

    return send_from_directory(WEB_DIR, path)

if __name__ == "__main__":
        app.run(host="0.0.0.0", port=5000)
