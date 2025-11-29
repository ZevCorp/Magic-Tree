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
    logging.info("Initializing Enchanted Tree Experience...")
    
    # Initialize Components
    hardware = HardwareManager()
    media = MediaManager()
    audio = AudioManager()
    messaging = MessagingService()

    logging.info("System Ready. Waiting for door...")

    while True:
        try:
            # 1. Wait for Door Open
            hardware.wait_for_door_open()
            logging.info("Door opened! Starting experience.")

            # 2. Play Intro Video (Santa)
            logging.info("=" * 50)
            logging.info("STEP 2: Playing intro video...")
            logging.info("=" * 50)
            media.play_video(INTRO_VIDEO_PATH)

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
            media.play_video(ASK_PHONE_VIDEO_PATH)

            # 5. Record Audio for Phone Number
            phone_audio_path = os.path.join(RECORDINGS_DIR, f"phone_audio_{timestamp}.wav")
            audio.record_audio(phone_audio_path, duration=8) # Give them 8 seconds

            # 6. Identify Phone Number
            logging.info("Processing phone number...")
            transcription = audio.transcribe_with_openai(phone_audio_path)
            phone_number = audio.extract_phone_number_with_assistant(transcription)

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

            logging.info("Experience finished. Resetting...")
            time.sleep(2) # Buffer before restarting

        except KeyboardInterrupt:
            logging.info("Stopping system...")
            break
        except Exception as e:
            logging.error(f"Unexpected error: {e}")
            time.sleep(5) # Wait before retrying

if __name__ == "__main__":
    main()
