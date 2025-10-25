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
mg.set(xlabel="Time (s)", ylabel="Moisture Sensor Reading (mV)", title="Moisture Readings Over Time")
mg.grid()
fig.savefig(current_time + "moisturegraph.png")
