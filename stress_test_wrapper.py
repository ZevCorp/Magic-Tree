#!/usr/bin/env python3
import time
import random
import logging
import threading
import sys
import os
from unittest.mock import MagicMock

# Configure logging to stdout
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [WRAPPER] - %(message)s')

# --- MOCKS ---

class MockAudioManager:
    def __init__(self):
        self.p = MagicMock()
        logging.info("MOCK: AudioManager initialized")

    def stop_background_music(self):
        # logging.info("MOCK: Stopped background music")
        pass

    def play_background_music(self):
        # logging.info("MOCK: Playing background music")
        pass

    def listen_for_keyword(self, stop_event, keyword="feliz navidad"):
        # Wait for a random time between 5 and 60 seconds to simulate standby
        # This is where we simulate the random start of the experience
        wait_time = random.uniform(5, 60)
        logging.info(f"MOCK: Standby (Waiting {wait_time:.1f}s for 'Feliz Navidad')...")
        
        # We check stop_event periodically to allow clean exit
        start_wait = time.time()
        while time.time() - start_wait < wait_time:
            if stop_event.is_set():
                return
            time.sleep(0.5)
            
        logging.info(f"MOCK: Keyword '{keyword}' detected! Triggering experience.")
        stop_event.set()
    
    def cleanup(self):
        logging.info("MOCK: AudioManager cleanup")

class MockPhoneInputSystem:
    def __init__(self, callback_fn=None):
        self.callback_fn = callback_fn
        self.running = True
        
    def start_processing(self):
        logging.info("MOCK: PhoneInputSystem start_processing called (User Dictating).")
        
        # Simulate time to dictate number (e.g. 5-15 seconds)
        dictation_time = random.uniform(5, 15)
        
        # We need to simulate updates to the UI
        mock_number_str = "3" + "".join([str(random.randint(0, 9)) for _ in range(9)])
        
        start_read = time.time()
        
        # Simulate typing/hearing digits one by one
        for i in range(1, 11):
            if not self.running: return None
            
            # Sleep portion of time
            time.sleep(dictation_time / 10)
            
            partial = mock_number_str[:i]
            if self.callback_fn:
                self.callback_fn(partial, "Escuchando...")
                
        # Simulate Verification Phase
        if self.callback_fn:
            self.callback_fn(mock_number_str, "Confirmar?")
            
        logging.info(f"MOCK: Phone number captured: {mock_number_str}. Waiting for confirmation...")
        
        # Simulate User saying "Confirmar" or "Si"
        time.sleep(2) 
        
        logging.info("MOCK: User confirmed.")
        return mock_number_str

    def stop(self):
        # logging.info("MOCK: PhoneInputSystem stopped")
        self.running = False
        
    def update_ui(self, status=None):
        pass

class MockMessagingService:
    def send_welcome_message(self, phone_number):
        logging.info(f"MOCK: Sending WhatsApp message to {phone_number}...")
        time.sleep(0.5)
        logging.info("MOCK: Message sent! (Simulated)")
        return True

# --- PATCHING ---
# We must patch before test_mode is fully executed/imported if it had side effects, 
# but test_mode mostly defines main(). Imports happen at top.
# We modify the modules after import but before main() runs.

import test_mode
import phone_manager
import messaging

# Patch Audio
test_mode.AudioManager = MockAudioManager

# Patch PhoneInputSystem (Used in test_mode inner loop)
# Since test_mode does 'from phone_manager import PhoneInputSystem' inside main loop,
# patching phone_manager.PhoneInputSystem will work.
phone_manager.PhoneInputSystem = MockPhoneInputSystem

# Patch Messaging
test_mode.MessagingService = MockMessagingService

if __name__ == "__main__":
    logging.info("STARTING STRESS TEST WRAPPER")
    logging.info("Press Ctrl+C to stop (Monitored by Master script)")
    
    try:
        # Run the actual test mode logic
        test_mode.main()
    except KeyboardInterrupt:
        logging.info("Wrapper stopping...")
    except Exception as e:
        logging.critical(f"WRAPPER CRASHED: {e}", exc_info=True)
        sys.exit(1)
