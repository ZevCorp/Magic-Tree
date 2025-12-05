#!/usr/bin/env python3
"""
Script de prueba para el Árbol Encantado
Ejecuta el sistema completo pero sin el sensor de puerta (modo MOCK para hardware)
La cámara, audio y todo lo demás funciona normalmente.
"""

import logging
import threading
import time
import os
from config import *
from hardware import HardwareManager
from media import MediaManager
from audio import AudioManager
from messaging import MessagingService

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    logging.info("=" * 60)
    logging.info("MODO DE PRUEBA - Árbol Encantado")
    logging.info("Experiencia completa SIN sensor de puerta")
    logging.info("=" * 60)
    
    # Initialize Components - Force mock mode ONLY for hardware
    hardware = HardwareManager(mock_mode=True)  # No door sensor
    media = MediaManager()  # Real camera
    audio = AudioManager()  # Real audio
    messaging = MessagingService()

    logging.info("Sistema listo.")
    logging.info("\nEn este modo:")
    logging.info("✓ La cámara se activará normalmente")
    logging.info("✓ El audio y detección de voz funcionan")
    logging.info("✓ Los videos se reproducen")
    logging.info("✗ El sensor de puerta está deshabilitado (presiona Enter)")
    logging.info("")

    while True:
        try:
            # 1. Wait for Door Open (MOCK - press Enter)
            hardware.wait_for_door_open()
            logging.info("Iniciando experiencia...")

            # 2. Play Intro Video (Santa)
            logging.info("=" * 50)
            logging.info("STEP 2: Playing intro video...")
            logging.info("=" * 50)
            if os.path.exists(INTRO_VIDEO_PATH):
                media.play_video(INTRO_VIDEO_PATH)
            else:
                logging.warning(f"Video no encontrado: {INTRO_VIDEO_PATH}")
                logging.info("Simulando reproducción (3 segundos)...")
                time.sleep(3)

            # 3. Record User (30 seconds fixed)
            logging.info("=" * 50)
            logging.info("STEP 3: Starting camera recording (30s)...")
            logging.info("Recording will stop automatically after 30 seconds.")
            logging.info("=" * 50)
            
            timestamp = int(time.time())
            user_video_path = os.path.join(RECORDINGS_DIR, f"user_video_{timestamp}.avi")
            
            # Start recording (blocks for 30 seconds)
            media.record_user(user_video_path)

            # 4. Ask for Phone Number
            logging.info("=" * 50)
            logging.info("STEP 4: Asking for phone number...")
            logging.info("=" * 50)
            if os.path.exists(ASK_PHONE_VIDEO_PATH):
                media.play_video(ASK_PHONE_VIDEO_PATH)
            else:
                logging.warning(f"Video no encontrado: {ASK_PHONE_VIDEO_PATH}")
                logging.info("Simulando video (3 segundos)...")
                time.sleep(3)
            
            # Give VLC time to release the display
            time.sleep(0.5)

            # 5. Record & Process Phone Number Continuously
            logging.info("=" * 50)
            logging.info("STEP 5: Starting continuous phone dictation...")
            logging.info("=" * 50)
            
            
            # Start Background Music
            audio.play_background_music()
            
            # Initialize PhoneDisplay
            from media import PhoneDisplay
            phone_display = PhoneDisplay()
            
            # Shared state
            full_transcript = ""
            final_phone_number = None
            audio_stop_event = threading.Event()
            
            def audio_worker():
                nonlocal full_transcript, final_phone_number
                logging.info("Audio worker started")
                
                # Process audio chunks
                for chunk_path in audio.stream_audio_chunks(audio_stop_event, chunk_duration=5):
                    if not phone_display.running: # Stop if UI closed
                        break

                    logging.info(f"Processing chunk: {chunk_path}")
                    chunk_text = audio.transcribe_with_openai(chunk_path)
                    
                    if chunk_text:
                        full_transcript += " " + chunk_text
                        logging.info(f"Full Transcript so far: {full_transcript}")
                        
                        # Extract number from accumulated text
                        extracted_number = audio.extract_phone_number_with_assistant(full_transcript)
                        
                        if extracted_number:
                            phone_display.update_number(extracted_number)
                            
                            # Check if we have enough digits (e.g., 10)
                            if len(extracted_number) >= 10:
                                logging.info(f"Found valid number: {extracted_number}")
                                final_phone_number = extracted_number
                                audio_stop_event.set() # Stop recording loop
                                phone_display.stop() # Stop UI loop
                                break
                    
                    # Cleanup chunk file
                    try:
                        os.remove(chunk_path)
                    except:
                        pass
                logging.info("Audio worker finished")

            # Start Audio Worker in Background Thread
            audio_thread = threading.Thread(target=audio_worker)
            audio_thread.start()
            
            # Run UI on Main Thread (Blocking)
            phone_display.run()
            
            # Ensure audio thread stops
            audio_stop_event.set()
            audio_thread.join()

            # Check if confirmed via keyboard
            if phone_display.confirmed:
                logging.info(f"Number confirmed via keyboard: {phone_display.number}")
                final_phone_number = phone_display.number

            if final_phone_number:
                # 6. Verification
                if not phone_display.confirmed:
                    logging.info("Waiting for user confirmation ('confirmar')...")
                    
                    confirm_event = threading.Event()
                    confirm_thread = threading.Thread(target=audio.listen_for_keyword, args=(confirm_event, "confirmar"))
                    confirm_thread.start()
                    
                    # Wait for confirmation
                    confirm_event.wait()
                    confirm_thread.join()
                
                audio.stop_background_music()
                
                # 7. Send Message & Save Metadata
                messaging.send_welcome_message(final_phone_number)
                
                # Save Metadata JSON
                metadata = {
                    "video_path": user_video_path,
                    "phone_number": final_phone_number,
                    "timestamp": timestamp,
                    "full_transcript": full_transcript
                }
                json_path = os.path.join(RECORDINGS_DIR, f"user_video_{timestamp}.json")
                import json
                with open(json_path, 'w') as f:
                    json.dump(metadata, f, indent=4)
                logging.info(f"Metadata saved to {json_path}")

            else:
                logging.warning("Could not identify phone number (timeout or manual stop).")
                audio.stop_background_music()

            logging.info("\n" + "=" * 60)
            logging.info("EXPERIENCIA COMPLETADA")
            logging.info("=" * 60)
            logging.info("Presiona Ctrl+C para salir o Enter para repetir...")
            
        except KeyboardInterrupt:
            logging.info("\nDeteniendo sistema...")
            break
        except Exception as e:
            logging.error(f"Error inesperado: {e}", exc_info=True)
            logging.info("Esperando 5 segundos antes de reintentar...")
            time.sleep(5)

if __name__ == "__main__":
    main()

