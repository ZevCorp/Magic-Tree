import cv2
import time
import logging
import os
import threading
import numpy as np
try:
    import vlc
    VLC_AVAILABLE = True
except ImportError:
    VLC_AVAILABLE = False
    logging.warning("python-vlc not found. Video playback will be mocked.")

WINDOW_NAME = "EnchantedTree"

class MediaManager:
    def __init__(self):
        self.vlc_instance = vlc.Instance('--fullscreen', '--no-video-title-show', '--mouse-hide-timeout=0') if VLC_AVAILABLE else None
        self.player = self.vlc_instance.media_player_new() if self.vlc_instance else None
        self.camera = None
        
        # Initialize Persistent Window
        try:
            logging.info(f"Initializing persistent window: {WINDOW_NAME}")
            cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
            cv2.setWindowProperty(WINDOW_NAME, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
            # Show black screen initially
            self.show_black_screen()
        except Exception as e:
            logging.warning(f"Could not initialize persistent window: {e}")

    def show_black_screen(self):
        """Helper to show a black screen on the persistent window."""
        try:
            black_img = np.zeros((1080, 1920, 3), dtype=np.uint8)
            cv2.imshow(WINDOW_NAME, black_img)
            cv2.waitKey(1)
        except Exception as e:
            logging.warning(f"Failed to show black screen: {e}")

    def check_for_enter(self, timeout_ms=50):
        """Checks for Enter key press on the persistent window."""
        try:
            key = cv2.waitKey(timeout_ms) & 0xFF
            if key == 13: # Enter
                return True
        except:
            pass
        return False

    def check_for_exit(self, timeout_ms=10):
        """Checks for ESC key press to exit the experience."""
        try:
            key = cv2.waitKey(timeout_ms) & 0xFF
            if key == 27: # ESC
                return True
        except:
            pass
        return False

    def play_video(self, video_path, check_interrupt=None):
        if not os.path.exists(video_path):
            # logging.error(f"Video file not found: {video_path}") 
            # Silent fail or just log warning? User said "omit it" for intro 2. 
            # We will just return, but let's log debug instead of error to reduce noise if intentional.
            logging.info(f"Video not found (skipping): {video_path}")
            return

        logging.info(f"Playing video: {video_path}")
        if self.player:
            # Ensure background is valid before launching VLC on top
            self.show_black_screen()
            
            media = self.vlc_instance.media_new(video_path)
            self.player.set_media(media)
            self.player.set_fullscreen(True)
            self.player.play()
            
            # Wait for video to slightly start to avoid immediate "Ended" state
            time.sleep(0.5) 
            
            while True:
                state = self.player.get_state()
                if state == vlc.State.Ended:
                    break
                if state == vlc.State.Error:
                    logging.error("VLC Error")
                    break
                
                # Check interruption
                if check_interrupt and check_interrupt():
                    logging.info("Video playback interrupted.")
                    self.player.stop()
                    break
                
                time.sleep(0.1)
            
            # Properly release fullscreen and stop
            self.player.set_fullscreen(False)
            self.player.stop()
            
            # Immediately show black screen again to prevent desktop flash
            self.show_black_screen()
             # Give window system time to clean up
            time.sleep(0.1) 
            logging.info("Video playback finished")
        else:
            logging.info("Mock playing video (3 seconds)...")
            start = time.time()
            while time.time() - start < 3:
                if check_interrupt and check_interrupt():
                     logging.info("Mock video interrupted")
                     return
                time.sleep(0.1)

    def show_image(self, image_path):
        """Displays a static image on the persistent window."""
        if not os.path.exists(image_path):
            logging.warning(f"Image not found: {image_path}")
            return
            
        try:
            img = cv2.imread(image_path)
            if img is not None:
                # Resize to fullscreen if needed (assuming 1920x1080)
                img = cv2.resize(img, (1920, 1080))
                cv2.imshow(WINDOW_NAME, img)
                cv2.waitKey(1)
            else:
                 logging.warning("Failed to load image")
        except Exception as e:
            logging.error(f"Error showing image: {e}")

    def record_user(self, output_path, stop_event=None):
        logging.info(f"Starting recording to {output_path}")
        logging.info("Opening camera...")
        self.camera = None
        # Try multiple indices to find the camera
        for index in range(4):
            logging.info(f"Attempting camera index {index}...")
            cap = cv2.VideoCapture(index)
            if cap.isOpened():
                self.camera = cap
                logging.info(f"Camera opened successfully on index {index}!")
                # Attempt to set 1080p resolution
                self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
                self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
                # Verify what we actually got
                actual_w = self.camera.get(cv2.CAP_PROP_FRAME_WIDTH)
                actual_h = self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT)
                logging.info(f"Requested 1920x1080, got {actual_w}x{actual_h}")
                break
            cap.release()
        
        if self.camera is None or not self.camera.isOpened():
            logging.error("Could not open camera on any index (0-3)")
            return

        # Define codec and create VideoWriter object
        # XVID is usually safe, or H264 if available
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        width = int(self.camera.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = 20.0 # Adjust based on camera
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

        logging.info(f"Camera resolution: {width}x{height} @ {fps}fps")
        # Ensure window properties
        cv2.setWindowProperty(WINDOW_NAME, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

        logging.info("Recording started! 30 seconds countdown...")
        frame_count = 0
        
        start_time = time.time()
        duration = 30
        
        while True:
            # Check if external stop was requested (optional now)
            if stop_event and stop_event.is_set():
                break

            elapsed = time.time() - start_time
            remaining = max(0, duration - int(elapsed))
            
            if remaining == 0:
                logging.info("Timer finished!")
                break

            ret, frame = self.camera.read()
            if ret:
                # Add countdown timer to frame
                # Bottom right corner
                text = str(remaining)
                font = cv2.FONT_HERSHEY_SIMPLEX
                font_scale = 4
                thickness = 8
                color = (255, 255, 255) # White
                
                text_size = cv2.getTextSize(text, font, font_scale, thickness)[0]
                text_x = width - text_size[0] - 50
                text_y = height - 50
                
                # Draw text with outline for better visibility
                cv2.putText(frame, text, (text_x, text_y), font, font_scale, (0, 0, 0), thickness + 4)
                cv2.putText(frame, text, (text_x, text_y), font, font_scale, color, thickness)

                out.write(frame)
                
                # Show in the persistent window
                cv2.imshow(WINDOW_NAME, frame)
                frame_count += 1
                
                # Check for 'q' key as manual fallback
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    logging.info("'q' key pressed, stopping recording")
                    break
            else:
                logging.warning("Failed to read frame from camera")
                break

        logging.info(f"Stopping recording... ({frame_count} frames captured)")
        self.camera.release()
        out.release()
        
        # Do NOT destroy window, just show black
        self.show_black_screen()
        
        logging.info("Camera released, returned to black screen")

    def cleanup(self):
        """Call this only when shutting down the app"""
        try:
            cv2.destroyAllWindows()
            if self.vlc_instance:
                self.vlc_instance.release()
        except:
            pass

    def display_verification_ui(self, number, stop_event):
        # Deprecated: Use PhoneDisplay class instead
        pass

class PhoneDisplay:
    def __init__(self):
        self.number = ""
        self.status = "Escuchando..."
        self.running = True
        self.confirmed = False
        self.lock = threading.Lock()
        self.window_name = WINDOW_NAME # Use the shared window
        
    def run(self):
        try:
            logging.info("PhoneDisplay started on main thread")
            from config import CHRISTMAS_BG_PATH
            
            # Load Background
            bg_img = None
            if os.path.exists(CHRISTMAS_BG_PATH):
                logging.info(f"Loading Christmas background from {CHRISTMAS_BG_PATH}")
                bg_img_raw = cv2.imread(CHRISTMAS_BG_PATH)
                if bg_img_raw is not None:
                     bg_img = cv2.resize(bg_img_raw, (1920, 1080))
            
            if bg_img is None:        
                logging.warning("Background not found or failed to load, using black")
                bg_img = np.zeros((1080, 1920, 3), dtype=np.uint8)

            font = cv2.FONT_HERSHEY_SIMPLEX
            
            # Ensure window properties (just in case)
            cv2.setWindowProperty(self.window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
            
            logging.info("Starting PhoneDisplay render loop")
            
            while self.running:
                img = bg_img.copy()
                
                with self.lock:
                    current_number = self.number
                    current_status = self.status
                
                # 1. Draw Phone Number
                if current_number:
                    font_scale_num = 5
                    thickness_num = 10
                    text_size_num = cv2.getTextSize(current_number, font, font_scale_num, thickness_num)[0]
                    text_x_num = (img.shape[1] - text_size_num[0]) // 2
                    text_y_num = (img.shape[0] // 2)
                    cv2.putText(img, current_number, (text_x_num, text_y_num), font, font_scale_num, (255, 255, 255), thickness_num)
                
                # 2. Draw Status/Instruction
                font_scale_inst = 2
                thickness_inst = 4
                text_size_inst = cv2.getTextSize(current_status, font, font_scale_inst, thickness_inst)[0]
                text_x_inst = (img.shape[1] - text_size_inst[0]) // 2
                text_y_inst = (img.shape[0] // 2) + 150
                cv2.putText(img, current_status, (text_x_inst, text_y_inst), font, font_scale_inst, (220, 220, 220), thickness_inst)

                # 3. Focus Instruction (Blinking)
                if int(time.time() * 2) % 2 == 0:
                    focus_text = "[ CLICK AQUI PARA ESCRIBIR ]"
                    font_scale_focus = 1.0
                    thickness_focus = 2
                    text_size_focus = cv2.getTextSize(focus_text, font, font_scale_focus, thickness_focus)[0]
                    text_x_focus = (img.shape[1] - text_size_focus[0]) // 2
                    text_y_focus = (img.shape[0]) - 50
                    cv2.putText(img, focus_text, (text_x_focus, text_y_focus), font, font_scale_focus, (100, 255, 100), thickness_focus)

                cv2.imshow(self.window_name, img)
                
                # Make sure it stays fullscreen (sometimes OS tries to shrink it)
                if int(time.time()) % 5 == 0:
                     cv2.setWindowProperty(self.window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

                key = cv2.waitKey(50) & 0xFF
                if key != 255: 
                    logging.info(f"Key pressed: {key}")
                    
                if key == ord('q'):
                    self.running = False
                elif key == 13: # Enter
                    logging.info("Enter pressed, confirming number")
                    self.confirmed = True
                    self.running = False
                elif key == 8: # Backspace
                    with self.lock:
                        self.number = self.number[:-1]
                elif 48 <= key <= 57: # 0-9
                    with self.lock:
                        self.number += chr(key)
            
            logging.info("PhoneDisplay loop ended")
            # Do NOT destroy window.
            # Just clear it to black
            black_img = np.zeros((1080, 1920, 3), dtype=np.uint8)
            cv2.imshow(self.window_name, black_img)
            cv2.waitKey(1)
            
        except Exception as e:
            logging.error(f"Error in PhoneDisplay: {e}", exc_info=True)

    def update_number(self, number):
        with self.lock:
            self.number = number

    def set_status(self, status):
        with self.lock:
            self.status = status

    def stop(self):
        self.running = False
