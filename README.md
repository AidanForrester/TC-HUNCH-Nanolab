# Tri County Substrate Nanolab - HUNCH

## Instalation Instructions

This module is written in Python 3.11.9 and HTML/CSS. The project must not use a new python version for compatibility with the Tesorflow Lite framework. Before completing the following instructions, ensure Python version 3.11.X is installed on the pi, even if a different version came with PI OS.

1. Clone this Repo using `git clone https://github.com/AidanForrester/TC-HUNCH-Nanolab.git/`
2. Open the project using `cd TC-HUNCH-Nanolab`
3. Designate the Dependency Installer an Executable `chmod +x InstallScript.sh`
4. Run the Install Script `./InstallScript.sh`
5. Enable I2C Through the PiConfig Menu

This will install the following dependencies:

- OpenCV For Camera Functions
- Adafruit Blinka Translation Layer + RPi.GPIO for CircuitPython
- BME680 CircuitPython Driver for Enviornmental Combo
- Adafruit ADC Driver for Moisture Sensors
- NeoPixel Library + RPi_WS281x for LEDs
- Flask Framework for Python to HTML Communication
- TF Lite Framework for AI Vision Model

## Usage Instructions

NeoPixels need sudo permissions in order to run in CircuitPython, so to start the script, use the following command:
``sudo /home/nanolab/labenv/bin/python /home/nanolab/TC-HUNCH-Nanolab/tests/ms.py``
