#!/usr/bin/env bash
set -euo pipefail

sudo apt update
sudo apt install -y python3 python3-pip python3-venv rtl-sdr

python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "[+] Environment ready. Run:"
echo "    source .venv/bin/activate"
echo "    python3 sdrrewind.py capture --freq 100e6 --buffer 60 --chunk 5"
