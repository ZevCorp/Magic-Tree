#!/bin/bash
# ============================================================
# Magic Tree Auto-Start Script with Visual Debug Log
# This script waits for all services to be ready and shows
# a visible log window for debugging startup issues.
# ============================================================

# Configuration
SCRIPT_DIR="/home/magicctree/Desktop/Magic-Tree"
LOG_FILE="$SCRIPT_DIR/logs/autostart_$(date +%Y%m%d_%H%M%S).log"
MAX_WAIT_DISPLAY=60    # Max seconds to wait for display
MAX_WAIT_AUDIO=30      # Max seconds to wait for audio
STARTUP_DELAY=10       # Initial delay after login

# Create logs directory
mkdir -p "$SCRIPT_DIR/logs"

# Logging function
log() {
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] $1" | tee -a "$LOG_FILE"
}

# ============================================================
# PHASE 0: Initial Wait
# ============================================================
log "=========================================="
log "Magic Tree AutoStart Iniciando..."
log "=========================================="
log "Esperando $STARTUP_DELAY segundos para que el sistema se estabilice..."
sleep $STARTUP_DELAY

# ============================================================
# PHASE 1: Wait for Display
# ============================================================
log "FASE 1: Esperando Display..."

wait_count=0
while [ $wait_count -lt $MAX_WAIT_DISPLAY ]; do
    # Check for X11 or Wayland display
    if [ -n "$DISPLAY" ] || [ -n "$WAYLAND_DISPLAY" ]; then
        # Test if we can actually open a window
        if xdpyinfo &>/dev/null || [ -n "$WAYLAND_DISPLAY" ]; then
            log "✓ Display disponible: DISPLAY=$DISPLAY, WAYLAND=$WAYLAND_DISPLAY"
            break
        fi
    fi
    
    wait_count=$((wait_count + 1))
    log "  Esperando display... ($wait_count/$MAX_WAIT_DISPLAY)"
    sleep 1
done

if [ $wait_count -ge $MAX_WAIT_DISPLAY ]; then
    log "✗ ERROR: No se pudo conectar al display después de ${MAX_WAIT_DISPLAY}s"
    exit 1
fi

# ============================================================
# PHASE 2: Wait for Audio (PulseAudio/ALSA)
# ============================================================
log "FASE 2: Esperando Audio..."

wait_count=0
while [ $wait_count -lt $MAX_WAIT_AUDIO ]; do
    # Try PulseAudio first
    if pactl info &>/dev/null; then
        log "✓ PulseAudio disponible"
        break
    fi
    
    # Fallback: check ALSA
    if aplay -l &>/dev/null; then
        log "✓ ALSA disponible (sin PulseAudio)"
        break
    fi
    
    wait_count=$((wait_count + 1))
    log "  Esperando audio... ($wait_count/$MAX_WAIT_AUDIO)"
    sleep 1
done

if [ $wait_count -ge $MAX_WAIT_AUDIO ]; then
    log "⚠ ADVERTENCIA: Audio puede no estar listo (continuando de todos modos)"
fi

# ============================================================
# PHASE 3: Show Log Window and Start Experience
# ============================================================
log "FASE 3: Iniciando experiencia con ventana de log..."

# Change to script directory
cd "$SCRIPT_DIR"

# Create a FIFO for real-time log display
LOG_FIFO="/tmp/magic_tree_log_$$"
mkfifo "$LOG_FIFO" 2>/dev/null || true

# Start zenity in background to show logs
# This creates a visible window that shows the startup log
(
    # Window title and properties
    zenity --text-info \
        --title="Magic Tree - Log de Inicio" \
        --width=800 \
        --height=500 \
        --font="monospace 10" \
        --filename="$LOG_FIFO" \
        2>/dev/null &
    ZENITY_PID=$!
    
    # Auto-close after 30 seconds if still showing
    sleep 30 && kill $ZENITY_PID 2>/dev/null &
) &

# Give zenity time to start
sleep 1

# Start tailing the log to the FIFO in background
(
    tail -f "$LOG_FILE" > "$LOG_FIFO" 2>/dev/null &
    TAIL_PID=$!
    
    # Kill tail when main script ends
    trap "kill $TAIL_PID 2>/dev/null; rm -f '$LOG_FIFO'" EXIT
    wait
) &

# ============================================================
# PHASE 4: Execute the main run_test.sh script
# ============================================================
log "=========================================="
log "Ejecutando run_test.sh..."
log "=========================================="

# Run the main script - output goes to both log file and to the log window FIFO
# Note: run_test.sh creates its own detailed log, this just captures startup
"$SCRIPT_DIR/run_test.sh" 2>&1 | while read line; do
    echo "$line" >> "$LOG_FILE"
    # Also show last few lines in zenity (if still open)
    echo "$line"
done

log "Script finalizado."

# Cleanup FIFO
rm -f "$LOG_FIFO"
