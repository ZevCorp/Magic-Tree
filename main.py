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
            media.play_video(ASK_PHONE_VIDEO_PATH)
            
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

            if final_phone_number:
                # 6. Verification
                logging.info("Waiting for user confirmation ('confirmar')...")
                # Re-initialize display for confirmation if needed, or just use console for now as requested "simple"
                # But we need to stop the music
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
