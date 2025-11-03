import adafruit_ccs811
from adafruit_bme280 import basic as adafruit_bme280
import digitalio
import board
import os

i2c_bus = board.I2C() ## Initialization of sensors
ccs811 = adafruit_ccs811.CCS811(i2c_bus, address=0x5B)
bme280 = adafruit_bme280.Adafruit_BME280_I2C(i2c_bus, address=0X77)
bme280.sea_level_pressure = 1013.25

while true
	print("CO2: %1.0f PPM" % ccs811.eco2)
	print("\nTemperature: %0.1f C" % bme280.temperature)
	print("Humidity: %0.1f %%" % bme280.humidity)
	time.sleep(3)
