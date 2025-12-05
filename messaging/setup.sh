#!/bin/bash
# Ensure we are in the script's directory
cd "$(dirname "$0")"

echo "Installing system dependencies..."
sudo apt-get update
# Try installing chromium (newer package name) or fallback to chromium-browser
sudo apt-get install -y chromium || sudo apt-get install -y chromium-browser
sudo apt-get install -y libgbm-dev

echo "Installing Node dependencies..."
npm install

echo "Setup complete. You can now run the messaging service."
