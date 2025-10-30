import ADS1x15
import adafruit_ccs811
from adafruit_bme280 import basic as adafruit_bme280
from picamzero import Camera

import digitalio
from datetime import datetime
import os

current_time = datetime.now() ##Setup for systematic photo system
photo_time = datetime.now()

i2c_bus = board.I2C() ## Initialization of sensors
ccs811 = adafruit_ccs811.CCS811(i2c_bus, address=0x5B)
bme280 = adafruit_bme280.Adafruit_BME280_I2C(i2c_bus, address=0X77)
ADS = ADS1x15.ADS1115(1, 0X48)
bme280.sea_level_pressure = 1013.25

f = ADS.toVoltage() ##Set parameters for Moisture sensors
ADS.setComparatorThresholdLow( 1.5 / f )
ADS.setComparatorThresholdHigh( 3 / f )
moistr = ADS.readADC(0)
moistl = ADS.readADC(1)

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

signalstart = digitalio.DigitalInOut(board.GP4) ##Initialize starting signal pin

while signalstart == 0: ##While a trial is not happening
  current_time = datetime.now() ##Read sensors and time
  moistr = ADS.readADC(0)
  moistl = ADS.readADC(1)
  if current_time - photo_time == 12 ##If it has been 12 hours since the last photo
    photo_time = current_time ##Take a photo and annotate it
    cam.annotate(photo_time + " - Internal Temperature: " + bme280.temperataure + " °C - Relative Humidity: " + bme280.relative_humidity + "% - Internal Co2:" + ccs811.eco2 + " ppm")
    cam.take_photo(f"/Desktop/PlantMonitoring/" + photo_time + ".jpg")
  if moist1 <= 2##If moisture sensors fall out of expected, send an error
    leftlowwater = 1
    ##Add message on web ui to check left sensor and water supply - this should not happen often
  if moistr <= 2
    rightlowwater = 1
    ##Add message on web ui to check right sensor and water supply - this should not happen often
  if moistl >= 2.75
    lefthighwater = 1
    ##Add message on web ui to check left sensor/overall condition of lab - this should not happen often
  if moistr >= 2.75
    righthighwater = 1
    ##Add message on web ui to check left sensor/overall condition of lab - this should not happen often
  if acctemp >= expectedtemp + 5  ##If temperature falls out of expected, send an error
    hightemp = 1
  if acctemp <= expectedtemp - 5 
    lowtemp = 1
  if errorreset == 1 ##If an error reset occers, clear all codes
    leftlowwater = 0
    lefthighwater = 0
    rightlowwater = 0
    righthighwater = 0
    lowtemp = 0
    hightemp = 0
