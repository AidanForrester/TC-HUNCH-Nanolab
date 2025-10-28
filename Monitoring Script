import ADS1x15
import adafruit_ccs811
from adafruit_bme280 import basic as adafruit_bme280
from picamzero import Camera

import digitalio
from datetime import datetime
import os

current_time = datetime.now()
photo_time = datetime.now()

i2c_bus = board.I2C()
ccs811 = adafruit_ccs811.CCS811(i2c_bus, address=0x5B)
bme280 = adafruit_bme280.Adafruit_BME280_I2C(i2c_bus, address=0X77)
ADS = ADS1x15.ADS1115(1, 0X48)

f = ADS.toVoltage()
ADS.setComparatorThresholdLow( 1.5 / f )
ADS.setComparatorThresholdHigh( 3 / f )
moistr = ADS.readADC(0)
moistl = ADS.readADC(1)

signalstart = digitalio.DigitalInOut(board.GP4)
leftlowwater = 0
lefthighwater = 0
rightlowwater = 0
righthighwater = 0
errorreset = 0

while signalstart == 0:
  current_time = datetime.now()
  moistr = ADS.readADC(0)
  moistl = ADS.readADC(1)
  if current_time - photo_time == 12
    photo_time = current_time
    cam.annotate(photo_time + " - Internal Temperature: " + bme280.temperataure + " °C - Relative Humidity: " + bme280.relative_humidity + "% - Internal Co2:" + ccs811.eco2 + " ppm")
    cam.take_photo(f"/Desktop/PlantMonitoring/" + photo_time + ".jpg")
  if moistl == 1.5
    leftlowwater = 1
    ##Add message on web ui to check left sensor and water supply - this should not happen often
  if moistr == 1.5
    rightlowwater = 1
    ##Add message on web ui to check right sensor and water supply - this should not happen often
  if moistl == 3
    lefthighwater = 1
    ##Add message on web ui to check left sensor/overall condition of lab - this should not happen often
  if moistr == 3
    righthighwater = 1
    ##Add message on web ui to check left sensor/overall condition of lab - this should not happen often
  if errorreset == 1
    leftlowwater = 0
    lefthighwater = 0
    rightlowwater = 0
    righthighwater = 0
