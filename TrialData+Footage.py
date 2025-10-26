import threading
import board
import digitalio
from datetime import datetime
import os

import ADS1x15
import adafruit_ccs811
from adafruit_bme280 import basic as adafruit_bme280
from picamzero import Camera

import matplotlib.pyplot as plt
import numpy as np

i2c_bus = board.I2C()
ccs811 = adafruit_ccs811.CCS811(i2c_bus, address=0x5B)
bme280 = adafruit_bme280.Adafruit_BME280_I2C(i2c_bus, address=0X77)
ADS = ADS1x15.ADS1115(1, 0X48)

f = ADS.toVoltage()
ADS.setComparatorThresholdLow( 1.5 / f )
ADS.setComparatorThresholdHigh( 3 / f )

current_time = datetime.now()
home_dir = os.environ['HOME'] 
cam = Camera()
cam.annotate(current_time + " - Internal Temperature: " + bme280.temperataure + " °C - Relative Humidity: " + bme280.relative_humidity + "% - Internal Co2:" + ccs811.eco2 + " ppm")


path = "Desktop/" + current_time + "moisturedata.txt"
with open(path,'w') as f:
    f.write('\n'.join("", current_time, ""))

signalstart = digitalio.DigitalInOut(board.GP4)

if signalstart == 1:
    cam.record_video(f"{home_dir}/Desktop/" + current_time + "trial.mp4", duration=5.18)
    path = "Desktop/footage.txt"
    with open(path,'w') as f:
        f.write('\n'.join(current_time, "/Desktop/" + current_time + "trial.mp4", "/Desktop/" + current_time + "moisturedata.txt", ""))

while digitalRead(signalstart) == 1:
    for i in range(26):
        timer = threading.Timer(.2, callback)
        moist1 = ADS.readADC(0)
        moist2 = ADS.readADC(1)
        path = "Desktop/" + current_time + "moisturedata.txt"
        with open(path,'w') as f:
            f.write('\n'.join(moist1, moist2, ""))
        timer.start()

path = "Desktop/" + current_time + "moisturedata.txt"
with open(path,'w') as f:
    f.write('\n'.join("end"))

##Moisture/Time Graph
fig, mg = plt.subplots()

with open(current_time + "moisturedata.txt", "r") as file_object:
    computingdata = file_object.readlines()

m1 = []

for i in computingdata:
    if i % 3 == 0:
        m1.append(i)

s = np.arrange(range(0, 5.18, 0.2))
e = np.arrange(int(m1))

m2 = []

for i in computingdata:
    if i % 3 == 1:
        m2.append(i)

t = np.arrange(int(m2))

mg.plot(s,e, label='Right Moisture Sensor', color=r)
mg.plot(s,t, label='Left Moisture Sensor', color=b)
mg.set(xlabel="Time (s)", ylabel="Moisture Sensor Reading (mV)", title="Moisture Readings Over Time/nInternal Temperature: " + bme280.temperataure + " °C - Relative Humidity: " + bme280.relative_humidity + "% - Internal Co2:" + ccs811.eco2 + " ppm")
mg.grid()
fig.savefig(current_time + "moisturegraph.png")
