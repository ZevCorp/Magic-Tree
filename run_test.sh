#!/bin/bash
# Script to run test_mode.py with X11 backend (avoiding Wayland issues)

# Force X11 backend for all applications
export GDK_BACKEND=x11
export QT_QPA_PLATFORM=xcb
export SDL_VIDEODRIVER=x11

# Disable Wayland for VLC
export VLC_PLUGIN_PATH=/usr/lib/aarch64-linux-gnu/vlc/plugins

# Force OpenCV to use X11
export OPENCV_VIDEOIO_PRIORITY_MSMF=0

echo "Starting Magic Tree Test Mode with X11 backend..."
echo "Environment configured:"
echo "  GDK_BACKEND=$GDK_BACKEND"
echo "  QT_QPA_PLATFORM=$QT_QPA_PLATFORM"
echo "  SDL_VIDEODRIVER=$SDL_VIDEODRIVER"
echo ""

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Load .env variables if file exists
if [ -f ".env" ]; then
    echo "Loading environment variables from .env..."
    set -o allexport
    source .env
    set +o allexport
fi

# Run the test mode
python test_mode.py
