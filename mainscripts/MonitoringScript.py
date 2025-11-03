from adafruit_ads1x15 import ADS1015, AnalogIn, ads1x15
import adafruit_ccs811
from adafruit_bme280 import basic as adafruit_bme280
from picamzero import Camera
from flask import Flask, Responses
import digitalio
import board
from datetime import datetime
import os
import threading
import time

app = Flask(__name__) ##Initialize Flask Framework to Communicate with Webserver

current_time = datetime.now() ##Setup for systematic photo system
photo_time = datetime.now()

i2c_bus = board.I2C() ## Initialization of sensors
ccs811 = adafruit_ccs811.CCS811(i2c_bus, address=0x5B)
bme280 = adafruit_bme280.Adafruit_BME280_I2C(i2c_bus, address=0X77)
ads = ADS1015(i2c_bus)
bme280.sea_level_pressure = 1013.25
cam = Camera()

moistr = AnalogIn(ads, ads1x15.Pin.A0)
moistl = AnalogIn(ads, ads1x15.Pin.A1)

expectedtemp = 71 ##Changeable settings for Temp to monitor for
acctemp = bme280.temperature

##Define error codes
leftlowwater = 0
lefthighwater = 0
rightlowwater = 0
righthighwater = 0
lowtemp = 0
hightemp = 0
errorreset = 0
systemhealthy = 1

signalstart = digitalio.DigitalInOut(board.GP4) ##Initialize starting signal pin
signalstart.direction = digitalio.Direction.INPUT
signalstart.pull = digitalio.Pull.UP 

@app.route("/temp")
def temp():
  return f"<p>{bme280.temperature:.2f} °C</p>"

@app.route("/lmoist")
def lmoist():
  return f"<p>{moistl.voltage:.2f} V (1.5-3)</p>"

@app.route("/rmoist")
def rmoist():
  return f"<p>{moistr.voltage:.2f} V (1.5-3)</p>"

@app.route("/eco2")
def co2():
  return f"<p>{ccs811.eco2:.2f} °C</p>"

@app.route("/health")
def systemhealth():
  if (systemhealthy == 1):
    return "<p>System Healthy</p>"
  else:
    return "<p>Check System!</p>"

def generate_frames():
  while True:
    frame = cam.capture_array
    yield (b' --frame\r\n'
           b'Content-Type: image/jpeg\r\n\r\n' +
           frame.tobytes() + b'\r\n')
    time.sleep(0.05)

@app.route('/videofeed')
def video_feed():
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')
  
def monitor_loop():
  global moistl, moistr, acctemp, leftlowwater, lefthighwater, rightlowwater, righthighwater, lowtemp, hightemp, errorreset, systemhealthy, photo_time
  while True:
    while signalstart.value:
      time.sleep(.5)
      continue

    while not signalstart.value: ##While a trial is not happening
      current_time = datetime.now() ##Read sensors and time
      readmoistl = moistl.voltage
      readmoistr = moistr.voltage
      acctemp = bme280.temperature
      current_time = datetime.now()
      errorcheck = leftlowwater + lefthighwater + rightlowwater + righthighwater + lowtemp + hightemp ##Checks if the system has any errors
      if (current_time - photo_time).seconds >= 12 * 3600: ##If it has been 12 hours since the last photo
          photo_time = current_time ##Take a photo and annotate it
          cam.annotate(f"{photo_time} - Internal Temperature: {bme280.temperature:.2f} °C - Relative Humidity: {bme280.relative_humidity:.2f}% - Internal CO2: {ccs811.eco2} ppm")
          cam.take_photo(f"/Desktop/PlantMonitoring/" + photo_time + ".jpg")
      if (moistl <= 2):##If moisture sensors fall out of expected, send an error
        leftlowwater = 1
        ##Add message on web ui to check left sensor and water supply - this should not happen often
      if (moistr <= 2):
        rightlowwater = 1
        ##Add message on web ui to check right sensor and water supply - this should not happen often
      if (moistl >= 2.75):
        lefthighwater = 1
        ##Add message on web ui to check left sensor/overall condition of lab - this should not happen often
      if (moistr >= 2.75):
        righthighwater = 1
        ##Add message on web ui to check left sensor/overall condition of lab - this should not happen often
      if (acctemp >= expectedtemp + 5):  ##If temperature falls out of expected, send an error
        hightemp = 1
      if (acctemp <= expectedtemp - 5):
        lowtemp = 1
      if (errorreset == 1): ##If an error reset occers, clear all codes
        leftlowwater = 0
        lefthighwater = 0
        rightlowwater = 0
        righthighwater = 0
        lowtemp = 0
        hightemp = 0
      if (errorcheck >= 1):
        systemhealthy = 0
      else:
        systemhealthy = 1
      time.sleep(5) ##Sleep so the CPU does not run at 100%
    
if __name__ == "__main__":
    t = threading.Thread(target=monitor_loop, daemon=True)
    t.start()
    app.run(host="0.0.0.0", port=5000)
