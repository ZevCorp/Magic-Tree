#!/usr/bin/env python3
"""Test script to verify live preview with v4l2loopback"""
import cv2
import os
import subprocess
import time
import numpy as np
import threading

print("="*50)
print("LIVE PREVIEW TEST with v4l2loopback")
print("="*50)

# Check devices
if not os.path.exists('/dev/video0'):
    print("ERROR: Camera /dev/video0 not found")
    exit(1)
    
if not os.path.exists('/dev/video10'):
    print("ERROR: Virtual camera /dev/video10 not found")
    print("Run: sudo modprobe v4l2loopback devices=1 video_nr=10 card_label='Preview' exclusive_caps=1")
    exit(1)

print("✓ Devices found")

# Start FFmpeg in background
duration = 6
cmd = [
    'ffmpeg', '-y',
    '-f', 'v4l2', '-video_size', '1280x720', '-framerate', '30',
    '-input_format', 'mjpeg', '-i', '/dev/video0',
    '-t', str(duration),
    '-filter_complex', '[0:v]transpose=1,split=2[rec][prev]',
    '-map', '[rec]', '-c:v', 'libx264', '-preset', 'ultrafast',
    '-pix_fmt', 'yuv420p', '/tmp/live_test.mp4',
    '-map', '[prev]', '-s', '720x1280', '-f', 'v4l2', '/dev/video10'
]

print("Starting FFmpeg...")
proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
time.sleep(1)  # Give FFmpeg time to start

# Open preview
print("Opening virtual camera...")
cap = cv2.VideoCapture('/dev/video10')
if not cap.isOpened():
    print("ERROR: Could not open virtual camera")
    proc.terminate()
    exit(1)

print("✓ Virtual camera opened")

# Create window
cv2.namedWindow("Preview Test", cv2.WINDOW_NORMAL)
cv2.resizeWindow("Preview Test", 360, 640)

start_time = time.time()
frame_count = 0

print("Showing preview... (Press 'q' to quit)")
while proc.poll() is None:
    ret, frame = cap.read()
    if ret:
        # Add overlay
        elapsed = time.time() - start_time
        remaining = max(0, int(duration - elapsed))
        
        # Red circle for REC
        cv2.circle(frame, (50, 50), 20, (0, 0, 255), -1)
        cv2.putText(frame, "REC", (80, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        cv2.putText(frame, str(remaining), (650, 1200), cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 4)
        
        cv2.imshow("Preview Test", frame)
        frame_count += 1
    
    if cv2.waitKey(33) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()

# Wait for FFmpeg
proc.wait()

print(f"\n✓ Preview showed {frame_count} frames in {duration} seconds")
print(f"  Average: {frame_count/duration:.1f} FPS")

# Check output
if os.path.exists('/tmp/live_test.mp4'):
    size = os.path.getsize('/tmp/live_test.mp4')
    print(f"✓ Recording saved: {size/1024:.1f} KB")
else:
    print("✗ Recording not saved!")

print("\nTest complete!")
