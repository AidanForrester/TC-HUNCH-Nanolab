# Tri County Substrate Nanolab - HUNCH

## Instalation Instructions

1. Flash the Pi with a 64 bit version of Raspberry Pi OS
2. Clone the reposatory using `https://github.com/AidanForrester/TC-HUNCH-Nanolab.git`
3. Open the diretory using `cd TC-HUNCH-Nanolab`
4. Designate the dependency installer an executable `chmod +x InstallScript.sh`
5. Run the Install Script `./InstallScript.sh`

This will install the following dependencies:

- Driver for Pi Camera
- Adafruit Blinka Translation Layer for CircuitPython
- CCS811 & BME280 CircuitPython Drivers for Enviornmental Combo
- ADC Driver for Moisture Sensors
