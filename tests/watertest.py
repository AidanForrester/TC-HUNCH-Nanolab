from adafruit_ads1x15 import ADS1115, AnalogIn, ads1x15
import digitalio
import board
import time

i2c_bus = board.I2C() ## Initialization of sensors
ads = ADS1115(i2c_bus)
moistl = AnalogIn(ads, ads1x15.Pin.A0)
moistr = AnalogIn(ads, ads1x15.Pin.A1)

while True:
        readmoistl = moistl.voltage
        readmoistr = moistr.voltage
        print(str(readmoistl) + " " + str(readmoistr))
        time.sleep(1)
