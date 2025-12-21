#!/bin/bash
# Script to run main.py with X11 backend (avoiding Wayland issues)

# Force X11 backend for all applications
export GDK_BACKEND=x11
export QT_QPA_PLATFORM=xcb
export SDL_VIDEODRIVER=x11

# Disable Wayland for VLC
export VLC_PLUGIN_PATH=/usr/lib/aarch64-linux-gnu/vlc/plugins

# Force OpenCV to use X11
export OPENCV_VIDEOIO_PRIORITY_MSMF=0

echo "Starting Magic Tree Experience with X11 backend..."
echo "Environment configured:"
echo "  GDK_BACKEND=$GDK_BACKEND"
echo "  QT_QPA_PLATFORM=$QT_QPA_PLATFORM"
echo "  SDL_VIDEODRIVER=$SDL_VIDEODRIVER"
echo ""

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Setup v4l2loopback for live preview during recording
echo "Setting up live preview..."
./setup_preview.sh
echo ""

# Load .env variables if file exists
if [ -f ".env" ]; then
    echo "Loading environment variables from .env..."
    set -o allexport
    source .env
    set +o allexport
fi

# Run the WhatsApp Bot in background
echo "Starting WhatsApp Bot..."
# Ensure OPENAI_API_KEY is exported if set in config.py (or we hope it's global)
# We assume the user has the key in env or we rely on the bot.js fallback/warning
(
    cd messaging || exit
    # Run in loop to auto-restart if crashes
    while true; do
        node bot.js
        echo "Bot crashed or stopped. Restarting in 5s..."
        sleep 5
    done
) &
BOT_PID=$!

# Run the main program
echo "Starting Main Application..."
python main.py

# Cleanup
echo "Main app exited. Stopping bot..."
kill $BOT_PID
