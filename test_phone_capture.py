#!/usr/bin/env python3
"""
Script de prueba para la captura de número telefónico LOCAL.
Usa faster-whisper para transcripción y pyttsx3 para feedback de voz.
"""

import logging
import threading
import time
import os
import re
from config import *
from audio import AudioManager, extract_digits_from_text
from media import PhoneDisplay

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    logging.info("=" * 60)
    logging.info("PRUEBA DE CAPTURA DE TELÉFONO (LOCAL)")
    logging.info("=" * 60)
    
    # Initialize Audio
    audio = AudioManager()
    
    # Check if local models are available
    if not audio.local_speech.model:
        logging.error("ERROR: faster-whisper model not loaded. Cannot proceed with local test.")
        return

    # Initialize Display
    phone_display = PhoneDisplay()
    
    # Shared state
    full_transcript = ""
    current_digits = ""
    audio_stop_event = threading.Event()
    
    def audio_worker():
        nonlocal full_transcript, current_digits
        logging.info("Audio worker started")
        
        # Process audio chunks
        for chunk_path in audio.stream_audio_chunks(audio_stop_event, chunk_duration=3):
            if not phone_display.running:
                break

            logging.info(f"Processing chunk: {chunk_path}")
            
            # 1. Local Transcription
            chunk_text = audio.local_speech.transcribe(chunk_path)
            
            if chunk_text:
                logging.info(f"Chunk text: {chunk_text}")
                
                # 2. Extract Digits
                new_digits = extract_digits_from_text(chunk_text)
                
                if new_digits:
                    logging.info(f"Found digits: {new_digits}")
                    
                    # 3. Update State
                    previous_digits = current_digits
                    current_digits += new_digits
                    
                    # 4. Update UI
                    phone_display.update_number(current_digits)
                    
                    # 5. TTS Feedback (speak only new digits)
                    # Speak digit by digit for clarity
                    spaced_digits = " ".join(list(new_digits))
                    audio.tts.speak(spaced_digits)
                    
                    # Check for completion (optional auto-stop)
                    if len(current_digits) >= 10:
                        logging.info("Reached 10 digits.")
            
            # Cleanup
            try:
                os.remove(chunk_path)
            except:
                pass
                
        logging.info("Audio worker finished")

    # Start Audio Worker
    audio_thread = threading.Thread(target=audio_worker)
    audio_thread.start()
    
    # Run UI (Blocking)
    logging.info("Starting UI... Press 'Enter' to confirm or 'q' to quit.")
    phone_display.run()
    
    # Stop Audio
    audio_stop_event.set()
    audio_thread.join()
    
    # Result
    if phone_display.confirmed:
        logging.info(f"CONFIRMED NUMBER: {phone_display.number}")
        audio.tts.speak(f"Número confirmado: {phone_display.number}")
    else:
        logging.info("Cancelled.")

    logging.info("Test complete.")

if __name__ == "__main__":
    main()
