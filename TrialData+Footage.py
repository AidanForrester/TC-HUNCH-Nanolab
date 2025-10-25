import threading
import board
import digitalio
from adafruit_seesaw.seesaw import Seesaw
from picamzero import Camera
from datetime import datetime
import os

import matplotlib.pyplot as plt
import numpy as np

i2c_bus = board.I2C()
ss1 = Seesaw(i2c_bus, addr=XXXX)
ss2 = Seesaw(i2c_bus, addr=XXXX)

current_time = datetime.now()
home_dir = os.environ['HOME'] 
cam = Camera()
cam.annotate(current_time)

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
        moist1 = ss1.moisture_read()
        moist2 = ss2.moisture_read()
        path = "Desktop/" + current_time + "moisturedata.txt"
        with open(path,'w') as f:
            f.write('\n'.join(moist1, moist2, ""))
        timer.start()

path = "Desktop/" + current_time + "moisturedata.txt"
with open(path,'w') as f:
    f.write('\n'.join("end"))

##Right Side Moisture/Time Graph
fig, mg1 = plt.subplots()

with open(current_time + "moisturedata.txt", "r") as file_object:
    computingdata = file_object.readlines()

m1 = []

for i in computingdata:
    if i % 3 == 0:
        m1.append(i)

s = np.arrange(range(0, 5.18, 0.2))
t = np.arrange(int(m1))

mg1.plot(s,t)
mg1.set(xlabel="Time (s)", ylabel="Right Moisture Sensor Reading (mV)", title="Right Moisture Sensor Readings Over Time")
mg1.grid()
fig.savefig(current_time + "rmoisturegraph.png")

##Left Side Moisture/Time Graph
fig, mg2 = plt.subplots()

with open(current_time + "moisturedata.txt", "r") as file_object:
    computingdata1 = file_object.readlines()

m2 = []

for i in computingdata1:
    if i % 3 == 1:
        m2.append(i)

s = np.arrange(range(0, 5.18, 0.2))
t = np.arrange(int(m2))

mg2.plot(s,t)
mg2.set(xlabel="Time (s)", ylabel="Right Moisture Sensor Reading (mV)", title="Left Moisture Sensor Readings Over Time")
mg2.grid()
fig.savefig(current_time + "lmoisturegraph.png")
