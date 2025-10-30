#!/bin/bash
sudo apt update

sudo apt install -y python3-pip python3-picamzero

python3 -m venv venv
source venv/bin/activate
pip install -U pip
