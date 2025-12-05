import cv2
import time
import logging
import os
import threading
try:
    import vlc
    VLC_AVAILABLE = True
except ImportError:
    VLC_AVAILABLE = False
    logging.warning("python-vlc not found. Video playback will be mocked.")

class MediaManager:
    def __init__(self):
        self.vlc_instance = vlc.Instance('--fullscreen', '--no-video-title-show', '--mouse-hide-timeout=0') if VLC_AVAILABLE else None
        self.player = self.vlc_instance.media_player_new() if self.vlc_instance else None
        self.camera = None

    def play_video(self, video_path):
        if not os.path.exists(video_path):
            logging.error(f"Video file not found: {video_path}")
            return

        logging.info(f"Playing video: {video_path}")
        if self.player:
            media = self.vlc_instance.media_new(video_path)
            self.player.set_media(media)
            self.player.set_fullscreen(True)
            self.player.play()
            
            # Wait for video to finish
            time.sleep(1) # Give it time to start
            while self.player.get_state() != vlc.State.Ended:
                if self.player.get_state() == vlc.State.Error:
                    logging.error("VLC Error")
                    break
                time.sleep(0.1)
            
            # Properly release fullscreen and stop
            self.player.set_fullscreen(False)
            self.player.stop()
            time.sleep(0.1)  # Give window system time to clean up
            logging.info("Video playback finished")
        else:
            logging.info("Mock playing video (3 seconds)...")
            time.sleep(3)

    def record_user(self, output_path, stop_event=None):
        logging.info(f"Starting recording to {output_path}")
        logging.info("Opening camera...")
        self.camera = cv2.VideoCapture(0)
        
        if not self.camera.isOpened():
            logging.error("Could not open camera")
            return

        logging.info("Camera opened successfully!")
        
        # Define codec and create VideoWriter object
        # XVID is usually safe, or H264 if available
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        width = int(self.camera.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = 20.0 # Adjust based on camera
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

        logging.info(f"Camera resolution: {width}x{height} @ {fps}fps")
        logging.info("Creating fullscreen window...")
        
        cv2.namedWindow("Recording", cv2.WND_PROP_FULLSCREEN)
        cv2.setWindowProperty("Recording", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

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
                cv2.imshow('Recording', frame)
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
        cv2.destroyAllWindows()
        logging.info("Camera released and window closed")

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
        self.window_name = "Phone Verification"
        
    def run(self):
        try:
            logging.info("PhoneDisplay started on main thread")
            import numpy as np
            from config import CHRISTMAS_BG_PATH
            
            # Create window with a more robust approach for Wayland/X11 compatibility
            logging.info(f"Creating window: {self.window_name}")
            
            # First create a normal window
            cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
            logging.info("Normal window created")
            
            # Load Background first (before setting fullscreen)
            if os.path.exists(CHRISTMAS_BG_PATH):
                logging.info(f"Loading Christmas background from {CHRISTMAS_BG_PATH}")
                bg_img = cv2.imread(CHRISTMAS_BG_PATH)
                if bg_img is None:
                    logging.error("Failed to load background image, using black")
                    bg_img = np.zeros((1080, 1920, 3), dtype=np.uint8)
                else:
                    bg_img = cv2.resize(bg_img, (1920, 1080))
                    logging.info("Background loaded successfully")
            else:
                logging.warning(f"Christmas background not found at {CHRISTMAS_BG_PATH}, using black.")
                bg_img = np.zeros((1080, 1920, 3), dtype=np.uint8)

            font = cv2.FONT_HERSHEY_SIMPLEX
            
            # Show initial frame before going fullscreen
            initial_img = bg_img.copy()
            text = "Escuchando..."
            text_size = cv2.getTextSize(text, font, 2, 4)[0]
            text_x = (initial_img.shape[1] - text_size[0]) // 2
            text_y = (initial_img.shape[0] // 2)
            cv2.putText(initial_img, text, (text_x, text_y), font, 2, (220, 220, 220), 4)
            cv2.imshow(self.window_name, initial_img)
            cv2.waitKey(1)
            logging.info("Initial frame displayed")
            
            # Now try to set fullscreen and topmost
            try:
                cv2.setWindowProperty(self.window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
                cv2.setWindowProperty(self.window_name, cv2.WND_PROP_TOPMOST, 1)
                logging.info("Window set to fullscreen and topmost")
            except Exception as e:
                logging.warning(f"Could not set window properties: {e}")
            
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

                cv2.imshow(self.window_name, img)
                
                # Force focus periodically (hacky but might help on some WMs)
                if int(time.time()) % 2 == 0: # Every 2 seconds roughly
                     cv2.setWindowProperty(self.window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

                key = cv2.waitKey(50) & 0xFF
                if key != 255: # 255 is what waitKey returns when no key is pressed on some systems
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
            
            logging.info("PhoneDisplay loop ended, destroying window")
            cv2.destroyWindow(self.window_name)
            logging.info("PhoneDisplay finished")
            
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
