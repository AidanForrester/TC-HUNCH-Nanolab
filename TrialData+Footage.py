import threading
import board
import digitalio
from adafruit_seesaw.seesaw import Seesaw
from picamzero import Camera
from datetime import datetime
import os

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

