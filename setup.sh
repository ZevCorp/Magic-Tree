#!/bin/bash

echo "Setting up Enchanted Tree Experience..."

# Update and install system dependencies
sudo apt-get update
sudo apt-get install -y python3-pip python3-venv vlc libvlc-dev portaudio19-dev libatlas-base-dev

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Create directories
mkdir -p assets recordings model

# Download Vosk Model (Small Spanish Model)
if [ ! -d "model/vosk-model-small-es-0.42" ]; then
    echo "Downloading Vosk Model..."
    wget https://alphacephei.com/vosk/models/vosk-model-small-es-0.42.zip
    unzip vosk-model-small-es-0.42.zip -d model/
    rm vosk-model-small-es-0.42.zip
else
    echo "Vosk Model already exists."
fi

echo "Setup Complete!"
echo "Please place 'intro.mp4' and 'ask_phone.mp4' in the 'assets' folder."
echo "Update 'config.py' with your Whisperflow API Key."
echo "Run with: source venv/bin/activate && python main.py"
