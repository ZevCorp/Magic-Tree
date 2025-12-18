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
echo "Installing Node.js dependencies..."
    npm install
echo "Freeing port 3000 if in use..."
fuser -k 3000/tcp || true
echo "Starting WhatsApp Server (Background)..."
node server.js > ../messaging_server.log 2>&1 &
SERVER_PID=$!
cd ..

echo "Messaging Server PID: $SERVER_PID"
echo "Waiting 10 seconds for server to initialize..."
sleep 10

# Check if server processes is still running
if ! ps -p $SERVER_PID > /dev/null; then
    echo "ERROR: Messaging Server died immediately!"
    echo "--- Server Log (Last 20 lines) ---"
    tail -n 20 messaging_server.log
    echo "----------------------------------"
    echo "Please check messaging_server.log for details."
    exit 1
fi


# Function to cleanup background process on exit
cleanup() {
    echo "Stopping Messaging Server (PID $SERVER_PID)..."
    kill $SERVER_PID
}
trap cleanup EXIT
# -----------------------------

# Run the test mode
# Create logs directory
mkdir -p logs
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="logs/run_test_$TIMESTAMP.txt"
echo "Logging execution to: $LOG_FILE"
echo "--- Run Started at $TIMESTAMP ---" > "$LOG_FILE"

# Run the test mode
# -u forces unbuffered binary stdout and stderr (so logs are written immediately)
# 2>&1 redirects stderr to stdout so we capture errors too
# tee -a appends to the log file while showing output on screen
python -u test_mode.py 2>&1 | tee -a "$LOG_FILE"
