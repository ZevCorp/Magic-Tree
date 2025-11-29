#!/bin/bash

echo "=========================================="
echo "Setting up Enchanted Tree Experience..."
echo "=========================================="

# Update system
echo "Updating system packages..."
sudo apt-get update

# Install system dependencies
echo "Installing system dependencies..."
sudo apt-get install -y \
    python3-pip \
    python3-venv \
    python3-dev \
    vlc \
    libvlc-dev \
    portaudio19-dev \
    python3-pyaudio \
    libatlas-base-dev \
    libjpeg-dev \
    libopenjp2-7 \
    libtiff5 \
    wget \
    unzip

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install Python dependencies one by one with error handling
echo "Installing Python dependencies..."

echo "  - Installing gpiozero..."
pip install gpiozero

echo "  - Installing opencv-python..."
pip install opencv-python

echo "  - Installing python-vlc..."
pip install python-vlc

echo "  - Installing vosk..."
pip install vosk

echo "  - Installing pyaudio..."
pip install pyaudio || {
    echo "  Trying alternative pyaudio installation..."
    pip install PyAudio --global-option="build_ext" --global-option="-I/usr/include" --global-option="-L/usr/lib"
}

echo "  - Installing requests..."
pip install requests

echo "  - Installing numpy..."
pip install numpy

# Create directories
echo "Creating project directories..."
mkdir -p assets recordings model

# Download Vosk Model (Small Spanish Model)
if [ ! -d "model/vosk-model-small-es-0.42" ]; then
    echo "Downloading Vosk Spanish Model..."
    cd model
    wget https://alphacephei.com/vosk/models/vosk-model-small-es-0.42.zip
    unzip vosk-model-small-es-0.42.zip
    rm vosk-model-small-es-0.42.zip
    cd ..
else
    echo "Vosk Model already exists."
fi

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Place 'intro.mp4' and 'ask_phone.mp4' in the 'assets' folder"
echo "2. Update 'config.py' with your Whisperflow API Key"
echo "3. Connect your door sensor to GPIO 17"
echo "4. Run with: source venv/bin/activate && python main.py"
echo ""
