#!/bin/bash
sudo apt update

sudo apt install -y python3-pip python3-picamzero

pip3 install --upgrade pip
pip3 install Adafruit-Blinka adafruit-circuitpython-ccs811 adafruit-circuitpython-bme280 adafruit-ads1x15 Flask
