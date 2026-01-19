#!/bin/bash
sudo apt update

python3.11 -m venv labvenv
source labvenv/bin/activate
pip install -U pip
pip install Adafruit-Blinka adafruit-circuitpython-bme680 adafruit-circuitpython-ads1x15 opencv-python Flask RPi.GPIO adafruit-circuitpython-neopixel rpi_ws281x
