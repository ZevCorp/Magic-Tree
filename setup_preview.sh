#!/bin/bash
# Setup script for live preview feature using v4l2loopback
# Run this before starting the Magic Tree experience

echo "========================================"
echo "Setting up v4l2loopback for live preview"
echo "========================================"

# Check if module is already loaded
if lsmod | grep -q v4l2loopback; then
    echo "✓ v4l2loopback module already loaded"
else
    echo "Loading v4l2loopback module..."
    sudo modprobe v4l2loopback devices=1 video_nr=10 card_label="Preview" exclusive_caps=1
    if [ $? -ne 0 ]; then
        echo "✗ Failed to load v4l2loopback module"
        echo "  Install with: sudo apt-get install v4l2loopback-dkms"
        exit 1
    fi
fi

# Wait for device to appear
sleep 0.5

# Verify device exists
if [ -e /dev/video10 ]; then
    echo "✓ Preview device /dev/video10 exists"
else
    echo "✗ Failed to create preview device"
    exit 1
fi

# Set permissions so non-root can access
echo "Setting permissions..."
sudo chmod 666 /dev/video10
if [ $? -eq 0 ]; then
    echo "✓ Permissions set (read/write for all users)"
else
    echo "✗ Failed to set permissions"
    exit 1
fi

# Create udev rule for persistence (optional, for auto-setup on reboot)
UDEV_RULE="/etc/udev/rules.d/99-v4l2loopback.rules"
if [ ! -f "$UDEV_RULE" ]; then
    echo "Creating udev rule for persistent permissions..."
    echo 'KERNEL=="video10", MODE="0666"' | sudo tee "$UDEV_RULE" > /dev/null
    sudo udevadm control --reload-rules
    echo "✓ Udev rule created"
fi

echo ""
echo "========================================"
echo "✓ Live preview setup complete!"
echo "  Camera: /dev/video0 (physical)"
echo "  Preview: /dev/video10 (virtual)"
echo "========================================"
