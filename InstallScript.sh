#!/bin/bash
sudo apt update

sudo apt install -y python3-pip python3-picamzero
sudo apt install -y libcamera-apps libcamera-tools

python3 -m venv venv
source venv/bin/activate
pip install -U pip
pip install Adafruit-Blinka adafruit-circuitpython-bme680 ADS1x15-ADC Flask
