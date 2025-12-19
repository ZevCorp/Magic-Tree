#!/usr/bin/env python3
import subprocess
import time
import sys
import logging
import threading
from datetime import datetime
import os

# --- CONFIGURATION ---
WRAPPER_SCRIPT = "stress_test_wrapper.py"
TIMEOUT_SECONDS = 300  # 5 minutes without output = FREEZE
LOG_FILE = "stress_test_detected_errors.log"

# --- LOGGING ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [MONITOR] - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("stress_test_monitor.log")
    ]
)

def log_error_to_file(message):
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now()}] {message}\n")
    except:
        pass

def reader_thread(process, last_seen_container):
    """Reads stdout from the process and checks for errors."""
    try:
        for line in iter(process.stdout.readline, ''):
            if not line:
                break
            
            # Print to our console so user can see it running
            print(line, end='') 
            
            # Update heartbeat
            last_seen_container[0] = time.time()
            
            # Analyze for Errors
            lower_line = line.lower()
            if "error" in lower_line or "exception" in lower_line or "traceback" in lower_line:
                # Ignore specific known benign warnings if any
                if "alsa" in lower_line or "jack server" in lower_line: 
                    continue # Ignore low-level audio warnings commonly seen on Pi
                
                logging.error(f"DETECTED ERROR IN OUTPUT: {line.strip()}")
                log_error_to_file(f"OUTPUT ERROR: {line.strip()}")
                
    except Exception as e:
        logging.error(f"Reader thread error: {e}")
    finally:
        try:
            process.stdout.close()
        except:
            pass

def main():
    logging.info("="*60)
    logging.info("CHAOS MONKEY / STRESS TEST MONITOR STARTED")
    logging.info(f"Target: {WRAPPER_SCRIPT}")
    logging.info(f"Timeout Threshold: {TIMEOUT_SECONDS} seconds")
    logging.info("="*60)
    
    restart_count = 0
    
    while True:
        logging.info(f"Starting execution #{restart_count + 1}...")
        
        # Start the wrapper process
        process = subprocess.Popen(
            [sys.executable, WRAPPER_SCRIPT],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, # Merge stderr into stdout to catch crashes
            text=True,
            bufsize=1 # Line buffered
        )
        
        # Shared container for heartbeat [timestamp]
        last_seen = [time.time()]
        
        # Start reader thread
        t = threading.Thread(target=reader_thread, args=(process, last_seen))
        t.daemon = True
        t.start()
        
        # Check loop
        running = True
        while running:
            # Check if process is still alive
            retcode = process.poll()
            
            if retcode is not None:
                # Process exited
                logging.warning(f"Process exited with code {retcode}")
                if retcode != 0:
                    log_error_to_file(f"CRASH: Process exited with code {retcode}")
                else:
                    logging.info("Process exited normally (unexpected for infinite loop script)")
                running = False
            
            # Check for Freeze
            time_since_last_output = time.time() - last_seen[0]
            if time_since_last_output > TIMEOUT_SECONDS:
                logging.error(f"FREEZE DETECTED! No output for {time_since_last_output:.1f}s")
                log_error_to_file(f"FREEZE: System hung for {TIMEOUT_SECONDS}s. Killing process.")
                
                # Kill process
                try:
                    process.kill()
                    process.wait(timeout=5)
                except:
                    pass
                running = False
            
            if running:
                time.sleep(1)
        
        # Cleanup before restart
        restart_count += 1
        logging.info(f"Restarting in 5 seconds... (Total Restarts: {restart_count})")
        time.sleep(5)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logging.info("Monitor stopped by user.")
