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
            # 1. Wait for Start (Door, Enter, or Voice)
            logging.info("Waiting for activation (Enter on Keypad/Window, 'Feliz Navidad', or Door Sensor)...")
            activation_event = threading.Event()
            
            # Helper to check all triggers
            def check_active():
                if activation_event.is_set(): return True
                # Check hardware (mock allows enter too, but we prioritize non-blocking)
                try:
                    if hardware.is_door_open():
                         logging.info("Door Open Detected!")
                         activation_event.set()
                         return True
                except:
                    pass
                
                # Check CV2 Enter
                if media.check_for_enter():
                    logging.info("Enter key detected on Window!")
                    activation_event.set()
                    return True
                return False

            # Standby Loop
            logging.info("Entering Standby Mode (Video/Image Loop)...")
            audio.stop_background_music() # Ensure no music during standby
            
            # Start Voice Listener
            def voice_listener():
               audio.listen_for_keyword(activation_event, "feliz navidad")
            
            # Daemon thread so it dies if main dies
            voice_thread = threading.Thread(target=voice_listener, daemon=True)
            voice_thread.start()

            while not activation_event.is_set():
                # 1. Play Standby Video
                if os.path.exists(STANDBY_VIDEO_PATH):
                     media.play_video(STANDBY_VIDEO_PATH, check_interrupt=check_active)
                
                if check_active(): break

                # 2. Show Standby Image
                if os.path.exists(STANDBY_IMAGE_PATH):
                    media.show_image(STANDBY_IMAGE_PATH)
                else:
                     # Fallback to black screen if no image, but try to be responsive
                     # We can't just block forever here.
                     pass

                # 3. Wait for 8 minutes (or trigger)
                # We check triggers frequently
                wait_start = time.time()
                VIDEO_INTERVAL = 8 * 60 # 8 minutes
                
                logging.info(f"Standby: Showing image, waiting {VIDEO_INTERVAL}s...")
                
                while time.time() - wait_start < VIDEO_INTERVAL:
                    if check_active(): 
                        break
                    time.sleep(0.05)
                
                if check_active(): break
            
            activation_event.set() # Ensure set in case loop exited otherwise
            logging.info("Iniciando experiencia...")

            # 2. Play Intro Video (Santa)
            logging.info("=" * 50)
            logging.info("STEP 2: Playing intro video...")
            logging.info("=" * 50)
            if os.path.exists(INTRO_VIDEO_PATH):
                media.play_video(INTRO_VIDEO_PATH)
                
                # 2.1 Play Second Intro Video
                logging.info("Playing second intro video...")
                # Optimized: silently skip if missing, no delay
                if os.path.exists(INTRO_VIDEO_2_PATH):
                    media.play_video(INTRO_VIDEO_2_PATH)
                else:
                    logging.info(f"Video no encontrado (skipping): {INTRO_VIDEO_2_PATH}")
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
            
            # Give system time to cleanup windows
            time.sleep(2.0)

            # 5. Record & Process Phone Number Continuously
            logging.info("=" * 50)
            logging.info("STEP 5: Starting continuous phone dictation...")
            logging.info("=" * 50)
            
            
            # 5. Record & Process Phone Number Continuously (NEW SYSTEM)
            logging.info("=" * 50)
            logging.info("STEP 5: Starting continuous phone dictation (Vosk)...")
            logging.info("=" * 50)
            
            # Start Background Music
            audio.play_background_music()
            
            # Initialize PhoneDisplay
            from media import PhoneDisplay
            phone_display = PhoneDisplay()
            
            # Initialize PhoneInputSystem
            from phone_manager import PhoneInputSystem
            
            final_phone_number = None

            # Definition of callback to update UI from Audio Thread
            def update_ui_callback(number_text, status_text=None):
                if phone_display.running:
                    phone_display.update_number(number_text)
                    if status_text:
                        phone_display.set_status(status_text)
            
            phone_system = PhoneInputSystem(callback_fn=update_ui_callback)

            def audio_worker():
                nonlocal final_phone_number
                logging.info("Audio worker started (Vosk)")
                # This blocks until confirmed or stopped
                final_phone_number = phone_system.start_processing()
                logging.info(f"Audio worker finished. Result: {final_phone_number}")
                
                # Close UI when done
                phone_display.confirmed = True # To signal main thread if it was waiting
                phone_display.stop()

            # Start Audio Worker
            audio_thread = threading.Thread(target=audio_worker)
            audio_thread.start()
            
            # Run UI on Main Thread (Blocking)
            phone_display.run()
            
            # Stop system if UI closed manually
            phone_system.stop()
            audio_thread.join()

            if final_phone_number:
                logging.info(f"Number captured and confirmed: {final_phone_number}")
                audio.stop_background_music()
                
                # 7. Send Message & Save Metadata
                messaging.send_welcome_message(final_phone_number)
                
                # Save Metadata JSON
                metadata = {
                    "video_path": user_video_path,
                    "phone_number": final_phone_number,
                    "timestamp": timestamp,
                    "full_transcript": "Vosk Dictation" 
                }
                json_path = os.path.join(RECORDINGS_DIR, f"user_video_{timestamp}.json")
                import json
                with open(json_path, 'w') as f:
                    json.dump(metadata, f, indent=4)
                logging.info(f"Metadata saved to {json_path}") 

                # 8. Goodbye Video
                logging.info("STEP 8: Playing goodbye video...")
                if os.path.exists(GOODBYE_VIDEO_PATH):
                    media.play_video(GOODBYE_VIDEO_PATH)
                else:
                    logging.info("Goodbye video not found, skipping.")

            else:
                logging.warning("Could not identify phone number (timeout or manual stop).")
                audio.stop_background_music()

            # Check for Exit Request
            if media.check_for_exit():
                logging.info("Exit requested via ESC key.")
                break

            logging.info("\n" + "=" * 60)
            logging.info("EXPERIENCIA COMPLETADA")
            logging.info("=" * 60)
            logging.info("Presiona Ctrl+C para salir o Enter para repetir (ESC para salir en ventana)...")
            
            media.show_black_screen()
            
            # Wait loop with exit check
            wait_start = time.time()
            while time.time() - wait_start < 2:
                if media.check_for_exit():
                     break
                time.sleep(0.1)

            if media.check_for_exit():
                break

        except KeyboardInterrupt:
            logging.info("\nDeteniendo sistema...")
            break
        except Exception as e:
            logging.error(f"Error inesperado: {e}", exc_info=True)
            logging.info("Esperando 5 segundos antes de reintentar...")
            time.sleep(5)

    if 'media' in locals():
        media.cleanup()

if __name__ == "__main__":
    main()

