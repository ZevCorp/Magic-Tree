#!/usr/bin/env python3
"""
Script de prueba para el Árbol Encantado
Ejecuta el sistema en modo MOCK sin necesidad de hardware
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
    logging.info("=== MODO DE PRUEBA - Árbol Encantado ===")
    logging.info("Este modo simula el hardware para pruebas")
    
    # Initialize Components in MOCK MODE
    hardware = HardwareManager(mock_mode=True)  # Force mock mode
    media = MediaManager()
    audio = AudioManager()
    messaging = MessagingService()

    logging.info("Sistema listo. Iniciando prueba...")

    try:
        # 1. Simulate Door Open
        logging.info("\n[1/6] Esperando apertura de puerta...")
        hardware.wait_for_door_open()
        
        # 2. Play Intro Video (or simulate if file doesn't exist)
        logging.info("\n[2/6] Reproduciendo video de introducción...")
        if os.path.exists(INTRO_VIDEO_PATH):
            media.play_video(INTRO_VIDEO_PATH)
        else:
            logging.warning(f"Video no encontrado: {INTRO_VIDEO_PATH}")
            logging.info("Simulando reproducción de video (3 segundos)...")
            time.sleep(3)

        # 3. Record User + Wait for "Feliz Navidad"
        logging.info("\n[3/6] Grabando usuario...")
        logging.info("En modo real, di 'Feliz Navidad' para terminar")
        logging.info("En modo prueba, esperaremos 5 segundos")
        
        timestamp = int(time.time())
        user_video_path = os.path.join(RECORDINGS_DIR, f"test_user_video_{timestamp}.avi")
        
        # Simulate recording for 5 seconds instead of waiting for keyword
        time.sleep(5)
        logging.info("Grabación simulada completada")

        # 4. Ask for Phone Number
        logging.info("\n[4/6] Solicitando número de teléfono...")
        if os.path.exists(ASK_PHONE_VIDEO_PATH):
            media.play_video(ASK_PHONE_VIDEO_PATH)
        else:
            logging.warning(f"Video no encontrado: {ASK_PHONE_VIDEO_PATH}")
            logging.info("Simulando video de solicitud (3 segundos)...")
            time.sleep(3)

        # 5. Get Phone Number (simulated)
        logging.info("\n[5/6] Capturando número de teléfono...")
        logging.info("En modo real, el usuario diría su número")
        
        # Simulate phone number
        phone_number = "3001234567"
        logging.info(f"Número simulado: {phone_number}")

        # 6. Send Message
        logging.info("\n[6/6] Enviando mensaje de bienvenida...")
        messaging.send_welcome_message(phone_number)

        logging.info("\n=== PRUEBA COMPLETADA EXITOSAMENTE ===")
        logging.info("El sistema está funcionando correctamente en modo simulación")

    except KeyboardInterrupt:
        logging.info("\nPrueba interrumpida por el usuario")
    except Exception as e:
        logging.error(f"Error durante la prueba: {e}", exc_info=True)

if __name__ == "__main__":
    main()
