#!/bin/bash
# Script to run test_mode.py with X11 backend (avoiding Wayland issues)
# AND start the WhatsApp Messaging Server

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

# Activate virtual environment
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Load .env variables
if [ -f ".env" ]; then
    echo "Loading environment variables from .env..."
    set -o allexport
    source .env
    set +o allexport
fi

# --- START MESSAGING SERVER ---
echo "--- Initializing Messaging Server ---"
cd messaging
if [ ! -d "node_modules" ]; then
    echo "Installing Node.js dependencies..."
    npm install
fi
echo "Starting WhatsApp Server (Background)..."
node server.js > ../messaging_server.log 2>&1 &
SERVER_PID=$!
cd ..

echo "Messaging Server PID: $SERVER_PID"
echo "Waiting 5 seconds for server to initialize..."
sleep 5

# Function to cleanup background process on exit
cleanup() {
    echo "Stopping Messaging Server (PID $SERVER_PID)..."
    kill $SERVER_PID
}
trap cleanup EXIT
# -----------------------------

# Run the test mode
python test_mode.py
