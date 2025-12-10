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
            # 1. Wait for Start (Door, Enter, or Voice Trigger)
            logging.info("Waiting for activation (Door, Enter, or 'Feliz Navidad')...")
            activation_event = threading.Event()
            
            # Start Voice Listener
            def voice_listener():
               audio.listen_for_keyword(activation_event, "feliz navidad")
            
            voice_thread = threading.Thread(target=voice_listener, daemon=True)
            voice_thread.start()
            
            # Helper to check all triggers
            def check_active():
                if activation_event.is_set(): return True
                if hardware.is_door_open():
                    logging.info("Door opened! Starting experience.")
                    activation_event.set()
                    return True
                if media.check_for_enter():
                    logging.info("Enter key detected!")
                    activation_event.set()
                    return True
                return False

            # Standby Loop
            logging.info("Entering Standby Mode (Video/Image Loop)...")
            audio.stop_background_music() # Ensure no music during standby

            while not activation_event.is_set():
                # 1. Play Standby Video
                if os.path.exists(STANDBY_VIDEO_PATH):
                     media.play_video(STANDBY_VIDEO_PATH, check_interrupt=check_active)
                
                if check_active(): break

                # 2. Show Standby Image
                if os.path.exists(STANDBY_IMAGE_PATH):
                    media.show_image(STANDBY_IMAGE_PATH)
                else:
                    media.show_black_screen()

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
            
            activation_event.set() # Signal audio thread to stop if it hasn't yet

            # 2. Play Intro Video (Santa)
            logging.info("=" * 50)
            logging.info("STEP 2: Playing intro video...")
            logging.info("=" * 50)
            media.play_video(INTRO_VIDEO_PATH)
            
            # 2.1 Play Second Intro Video
            logging.info("Playing second intro video...")
            # play_video now silently skips if not found, fulfilling the request to optimize/omit
            media.play_video(INTRO_VIDEO_2_PATH)

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

            # Check if confirmed via keyboard
            if phone_display.confirmed:
                logging.info(f"Number confirmed via keyboard: {phone_display.number}")
                final_phone_number = phone_display.number

            if final_phone_number:
                # 6. Verification
                if not phone_display.confirmed:
                    logging.info("Waiting for user confirmation ('confirmar')...")
                    # Re-initialize display for confirmation if needed, or just use console for now as requested "simple"
                    # But we need to stop the music
                    
                    # NOTE: Since we closed the UI, we can't show "Di Confirmar" on screen easily without reopening.
                    # For now, we rely on voice command blind, or we could restart UI.
                    # Given "simple" requirement and previous context, we'll just wait for voice.
                    
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
                
                # 8. Goodbye Video
                logging.info("STEP 8: Playing goodbye video...")
                if os.path.exists(GOODBYE_VIDEO_PATH):
                    media.play_video(GOODBYE_VIDEO_PATH)

            else:
                logging.warning("Could not identify phone number (timeout or manual stop).")
                audio.stop_background_music()
                logging.warning("Could not identify phone number.")

            # Check for Exit Request
            if media.check_for_exit():
                logging.info("Exit requested via ESC key.")
                break

            logging.info("Experience finished. Resetting...")
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
            logging.info("Stopping system...")
            break
        except Exception as e:
            logging.error(f"Unexpected error: {e}")
            time.sleep(5) # Wait before retrying

    if 'media' in locals():
        media.cleanup()

if __name__ == "__main__":
    main()
