import threading
import board
import digitalio
from datetime import datetime
import os

from adafruit_ads1x15 import ADS1015, AnalogIn, ads1x15
import adafruit_ccs811
from adafruit_bme280 import basic as adafruit_bme280
from picamzero import Camera

import matplotlib.pyplot as plt
import numpy as np

i2c_bus = board.I2C()
ccs811 = adafruit_ccs811.CCS811(i2c_bus, address=0x5B)
bme280 = adafruit_bme280.Adafruit_BME280_I2C(i2c_bus, address=0X77)
ads = ADS1015(i2c_bus)

moistr = AnalogIn(ads, ads1x15.Pin.A0)
moistl = AnalogIn(ads, ads1x15.Pin.A1)

current_time = datetime.now()
home_dir = os.environ['HOME'] 
cam = Camera()
cam.annotate(f"{current_time} - Internal Temperature: {bme280.temperature:.2f} °C - Relative Humidity: {bme280.relative_humidity:.2f}% - Internal CO2: {ccs811.eco2} ppm")

signalstart = digitalio.DigitalInOut(board.GP4)

if signalstart.value == 1:
    cam.record_video(f"{home_dir}/Desktop/TrialFootage" + current_time + "trial.mp4", duration=5.18)
    path = "Desktop/footage.txt"
    with open(path,'w') as f:
                f.write('\n'.join([str(current_time),
                           f"/Desktop/{current_time}_trial.mp4",
                           f"/Desktop/{current_time}_moisturedata.txt", ""]))
        
while signalstart.value == 1:
    for i in range(26):
        time.sleep(.2)
        readmoistl = moistl.voltage
        readmoistr = moistr.voltage
        path = os.path.join(home_dir, "Desktop/TrialData", f"{current_time}_moisturedata.txt")
        with open(path,'w') as f:
            f.write('\n'.join([str(moist1), str(moist2), ""]))
        timer.start()

path = os.path.join(home_dir, "Desktop/TrialData", f"{current_time}_moisturedata.txt")
with open(path,'a') as f:
    f.write("end\n")

##Moisture/Time Graph
fig, mg = plt.subplots()

with open(os.path.join(home_dir, "Desktop/TrialData", f"{current_time}_moisturedata.txt"), "r") as file_object:
    computingdata = file_object.readlines()

m1 = []

for idx, i in enumerate(computingdata):
    if idx % 3 == 0:
        m1.append(float(i.strip()))

s = np.arrange(range(0, 5.18, 0.2))
e = np.arrange(int(m1))

m2 = []

for idx, i in enumerate(computingdata):
    if idx % 3 == 1:
        m1.append(float(i.strip()))

t = np.arrange(int(m2))

mg.plot(s,e, label='Right Moisture Sensor', color='r')
mg.plot(s,t, label='Left Moisture Sensor', color='b')
title=f"Moisture Readings Over Time (1.5-3V)\nInternal Temperature: {bme280.temperature:.2f} °C - Relative Humidity: {bme280.relative_humidity:.2f}% - Internal CO2: {ccs811.eco2} ppm")
mg.grid()
fig.savefig(os.path.join(home_dir, "Desktop/TrialResultGraphs", f"{current_time}_moisturegraph.png"))
