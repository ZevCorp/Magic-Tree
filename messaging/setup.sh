#!/bin/bash
# Ensure we are in the script's directory
cd "$(dirname "$0")"

echo "Installing system dependencies..."
sudo apt-get update
sudo apt-get install -y chromium-browser libgbm-dev

echo "Installing Node dependencies..."
npm install

echo "Setup complete. You can now run the messaging service."
