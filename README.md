# Tri County Substrate Nanolab - HUNCH

## Instalation Instructions

1. Flash the Pi with a 64 bit Version of Raspberry Pi OS
2. Clone the Repo using `git clone https://github.com/AidanForrester/TC-HUNCH-Nanolab.git/`
3. Create a python virtual enviornment for the libraries `python3 -m venv --system-site-packages nanolabenvenv`
4. Open the project using `cd TC-HUNCH-Nanolab`
5. Designate the Dependency Installer an Executable `chmod +x InstallScript.sh`
6. Run the Install Script `./InstallScript.sh`
7. Enable I2C Through the PiConfig Menu

This will install the following dependencies:

- OpenCV For Camera Functions
- ONNX Runtime for AI Vision Model
- Adafruit Blinka Translation Layer for CircuitPython
- BME680 CircuitPython Driver for Enviornmental Combo
- Adafruit ADC Driver for Moisture Sensors
- NeoPixel Library for LEDs
- Flask Framework for Python to HTML Communication

## Usage Instructions
To make the program work, you must work in a python virtual enviornment:
``source nanolabenv/bin/activate``

NeoPixels also need sudo permissions in order to run in CircuitPython, so to start the script, use the following command:
``sudo /home/nanolab/nanolabenv/bin/python /home/nanolab/TC-HUNCH-Nanolab/tests/ms.py``
