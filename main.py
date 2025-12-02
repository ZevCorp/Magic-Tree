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
            
            # Give VLC time to release the display
            time.sleep(0.5)

            # 5. Record & Process Phone Number Continuously
            logging.info("=" * 50)
            logging.info("STEP 5: Starting continuous phone dictation...")
            logging.info("=" * 50)
            
            # Start Background Music
            audio.play_background_music()
            
            # Start UI Thread immediately
            from media import PhoneDisplay
            phone_display = PhoneDisplay()
            phone_display.start()
            
            full_transcript = ""
            final_phone_number = None
            audio_stop_event = threading.Event()
            
            # Process audio chunks
            for chunk_path in audio.stream_audio_chunks(audio_stop_event, chunk_duration=5):
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
                            break
                
                # Cleanup chunk file
                try:
                    os.remove(chunk_path)
                except:
                    pass

            if final_phone_number:
                # 6. Verification
                logging.info("Waiting for user confirmation ('confirmar')...")
                phone_display.set_status("Di 'Confirmar' para continuar")
                
                confirm_event = threading.Event()
                confirm_thread = threading.Thread(target=audio.listen_for_keyword, args=(confirm_event, "confirmar"))
                confirm_thread.start()
                
                # Wait for confirmation
                confirm_event.wait()
                confirm_thread.join()
                
                phone_display.stop()
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
                phone_display.stop()
                audio.stop_background_music()
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
