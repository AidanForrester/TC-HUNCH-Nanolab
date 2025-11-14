#!/bin/bash
sudo apt update

python3 -m venv venv
source venv/bin/activate
pip install -U pip
pip install Adafruit-Blinka adafruit-circuitpython-bme680 adafruit-circuitpython-ads1x15 opencv-python Flask