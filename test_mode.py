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

            # 3. Record User + Wait for "Feliz Navidad"
            logging.info("=" * 50)
            logging.info("STEP 3: Starting camera recording...")
            logging.info("Say 'Feliz Navidad' to stop recording")
            logging.info("=" * 50)
            
            timestamp = int(time.time())
            user_video_path = os.path.join(RECORDINGS_DIR, f"user_video_{timestamp}.avi")
            
            stop_event = threading.Event()
            # Start listening for keyword in background
            listener_thread = threading.Thread(target=audio.listen_for_keyword, args=(stop_event,))
            listener_thread.start()
            
            # Start recording (blocks until stop_event is set)
            media.record_user(user_video_path, stop_event)
            
            # Ensure listener thread stops if recording ended manually
            stop_event.set()
            listener_thread.join(timeout=1)

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

            # 5. Record Audio for Phone Number
            logging.info("=" * 50)
            logging.info("STEP 5: Recording phone number...")
            logging.info("=" * 50)
            phone_audio_path = os.path.join(RECORDINGS_DIR, f"phone_audio_{timestamp}.wav")
            audio.record_audio(phone_audio_path, duration=8)

            # 6. Identify Phone Number
            logging.info("=" * 50)
            logging.info("STEP 6: Processing phone number...")
            logging.info("=" * 50)
            transcription = audio.transcribe_with_openai(phone_audio_path)
            phone_number = audio.extract_phone_number_with_assistant(transcription)

            if phone_number:
                logging.info(f"Identified Phone Number: {phone_number}")
                
                # Display the number and wait for "Confirmar"
                logging.info("Waiting for user confirmation ('confirmar')...")
                confirm_event = threading.Event()
                
                # Start listening for "confirmar"
                confirm_thread = threading.Thread(target=audio.listen_for_keyword, args=(confirm_event, "confirmar"))
                confirm_thread.start()
                
                # Show UI (blocks until confirm_event is set)
                media.display_verification_ui(phone_number, confirm_event)
                
                # Ensure thread joins
                confirm_event.set()
                confirm_thread.join(timeout=1)

                # 7. Send Message & Save Metadata
                messaging.send_welcome_message(phone_number)
                
                # Save Metadata JSON
                metadata = {
                    "video_path": user_video_path,
                    "phone_number": phone_number,
                    "timestamp": timestamp,
                    "phone_audio_path": phone_audio_path
                }
                json_path = os.path.join(RECORDINGS_DIR, f"user_video_{timestamp}.json")
                import json
                with open(json_path, 'w') as f:
                    json.dump(metadata, f, indent=4)
                logging.info(f"Metadata saved to {json_path}")

            else:
                logging.warning("Could not identify phone number.")

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

