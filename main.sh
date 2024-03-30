#!/bin/bash

# Setup environment
pip install -r requirements.txt

# Get databases from OneDrive if they exist
cp -r /mnt/c/Users/joshm/OneDrive/db .

# Clear any previous log data
echo -n > /logs/regulator.log
echo -n > logs/debug.log

# Clear any previously generated data
rm -rf feeds
rm -rf regulator
rm -rf rules
mkdir feeds

# Get latest scopes
python3 src/yeswehack.py
python3 src/hackerone.py
python3 src/bugcrowd.py
python3 src/integriti.py

# Subdomains
python3 src/recon/subfinder.py
python3 src/recon/regulator.py

# Remove Subdomains that are out of scope
python3 /src/recon/remove_out_of_scope.py

# Copy Databases to OneDrive to bve saved
cp -r db /mnt/c/Users/joshm/OneDrive