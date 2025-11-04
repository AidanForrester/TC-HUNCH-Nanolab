import adafruit_ccs811
from adafruit_bme280 import basic as adafruit_bme280
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
bme280 = adafruit_bme280.Adafruit_BME280_I2C(i2c_bus)
bme280.sea_level_pressure = 1013.25
try:
        ccs811 = adafruit_ccs811.CCS811(i2c_bus, address = 0x5B)
except (ValueError, RuntimeError, OSError) as e:
    print("CCS811 not ready:", e)
    ccs811 = None

@app.route('/sensor_data')
def sensor_data():
    humidity = round(bme280.humidity, 1)
    temperature = round(bme280.temperature, 1)
    co2 = round(ccs811.eco2, 0) if ccs811 and getattr(ccs811, "data_ready", False) else None
    return jsonify({'humidity': humidity, 'temperature': temperature, 'co2': co2})

@app.route('/', defaults={'path': 'index.html'})
@app.route('/<path:path>')
def serve_page(path):

    return send_from_directory(WEB_DIR, path)

def main_loop():
        while True:
                try:
                        print("CO2: %1.0f PPM" % ccs811.eco2)
                except:
                        print("CCS811 not ready")
                print("\nTemperature: %0.1f C" % bme280.temperature)
                print("Humidity: %0.1f %%" % bme280.humidity)
                time.sleep(3)

if __name__ == "__main__":
        t = threading.Thread(target=main_loop, daemon=True)
        t.start()
        app.run(host="0.0.0.0", port=5000)
