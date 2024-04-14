#!/bin/bash

# Setup environment
pip install -r requirements.txt

# Clear any previous log data
echo -n > logs/debug.log

# Clear any previously generated data
rm -rf feeds
rm -rf httpx
rm -rf katana

mkdir feeds
mkdir httpx
mkdir katana

# Get latest scopes
#python3 src/yeswehack.py
python3 src/recon/hackerone.py
#python3 src/bugcrowd.py
#python3 src/integriti.py

python3 src/helpers/get_latest_resolvers.py

# Subdomains
python3 src/recon/subfinder.py
#python3 src/recon/alterx.py
#python3 src/recon/regulator.py

python3 src/recon/dnsx.py

# Remove Subdomains that are out of scope
python3 src/helpers/remove_out_of_scope.py

python3 src/recon/httpx.py

python3 src/recon/katana.py

#python3 src/recon/nuclei.py

# Copy Databases to OneDrive to bve saved
current_date=$(date +'%Y-%m-%d')
tar -czf swarm-$current_date.tar.gz swarm.db swarm-url.db
mv swarm-$current_date.tar.gz /mnt/c/Users/joshm/OneDrive/bbdb