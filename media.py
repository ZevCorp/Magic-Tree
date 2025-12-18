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
        # Add '--avcodec-hw=none' to disable hardware acceleration which causes segfaults if v4l2m2m state is bad
        # The script-based fix disabled the *access* plugin for v4l2, but the *codec* plugin (v4l2m2m) is still active in ffmpeg/avcodec.
        # We must explicitly tell VLC's internal ffmpeg wrapper to IGNORE the v4l2m2m codec.
        self.vlc_instance = vlc.Instance(
            '--fullscreen', 
            '--no-video-title-show', 
            '--mouse-hide-timeout=0',
            # This is the magic bullet: specifically blacklist the crashing v4l2m2m codec
            '--codec=avcodec,all', 
            '--avcodec-skip-frame=0', 
            '--avcodec-skip-idct=0', 
            # '--avcodec-hw=none' was too broad, let's try specific overrides if available, or just none for safety
            '--avcodec-hw=none'
        ) if VLC_AVAILABLE else None
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
                # Attempt to set MJPEG first (crucial for high FPS at high res on USB)
                self.camera.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
                
                # Attempt to set 1080p resolution
                # Attempt to set 1080p resolution
                self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
                self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
                self.camera.set(cv2.CAP_PROP_FPS, 30)

                # --- CAMERA ADJUSTMENTS REMOVED (NATURAL LOOK) ---
                
                # Verify what we actually got
                actual_w = self.camera.get(cv2.CAP_PROP_FRAME_WIDTH)
                actual_h = self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT)
                actual_fps = self.camera.get(cv2.CAP_PROP_FPS)
                logging.info(f"Requested 1920x1080 @ 30fps MJPEG. Got: {actual_w}x{actual_h} @ {actual_fps}fps")
                break
            cap.release()
        
        if self.camera is None or not self.camera.isOpened():
            logging.error("Could not open camera on any index (0-3)")
            return

        # Define codec and create VideoWriter object
        # XVID is usually safe, or H264 if available
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        
        # Natural Input Dimensions (No Swap)
        width = int(self.camera.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        fps = 30.0 # Target 30 FPS
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

        logging.info(f"Recording Video: {width}x{height} @ {fps}fps")
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
                # Rotate Frame 90 Degrees
                frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)

                # --- 1. WRITE TO FILE (Raw Vertical Video) ---
                # We save the full resolution vertical video
                
                # Add timer to the raw frame (adjusted for vertical layout)
                # Frame is now Height x Width (e.g. 1920x1080 -> 1080x1920)
                f_h, f_w = frame.shape[:2]
                
                text = str(remaining)
                font = cv2.FONT_HERSHEY_SIMPLEX
                font_scale = 4
                thickness = 8
                color = (255, 255, 255)
                
                text_size = cv2.getTextSize(text, font, font_scale, thickness)[0]
                text_x = f_w - text_size[0] - 50
                text_y = f_h - 50
                
                cv2.putText(frame, text, (text_x, text_y), font, font_scale, (0, 0, 0), thickness + 4)
                cv2.putText(frame, text, (text_x, text_y), font, font_scale, color, thickness)
                
                out.write(frame)

                # --- 2. PREPARE FOR DISPLAY (Pillarbox/Letterbox) ---
                # Screen is 1920x1080 (Landscape)
                # Image is Vertical (e.g. 1080x1920)
                # We need to scale image to fit Height 1080.
                
                screen_w = 1920
                screen_h = 1080
                
                # Scale factor to fit height
                scale = screen_h / f_h
                new_w = int(f_w * scale)
                new_h = int(f_h * scale) # Should be 1080
                
                resized_frame = cv2.resize(frame, (new_w, new_h))
                
                # Create Black Background
                display_img = np.zeros((screen_h, screen_w, 3), dtype=np.uint8)
                
                # Center offset
                x_offset = (screen_w - new_w) // 2
                
                # Copy into center
                # Ensure bounds
                if x_offset >= 0:
                     display_img[:, x_offset:x_offset+new_w] = resized_frame
                
                cv2.imshow(WINDOW_NAME, display_img)
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

    def get_camera(self):
        """Helper to find and open a working camera"""
        for index in range(4):
            cap = cv2.VideoCapture(index)
            if cap.isOpened():
                # Apply settings
                cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
                return cap
            cap.release()
        return None

    def monitor_standby(self, duration, check_interrupt):
        """
        Monitors for face detection for 'duration' seconds.
        Returns:
           'INTERRUPT': if check_interrupt() becomes True (Start Exp)
           'FACE': if face detected (Play Video)
           'TIMEOUT': if duration ends (Play Video)
        """
        logging.info(f"Monitoring standby for {duration} seconds (Face Detection Active)...")
        
        # Load Haar Cascade
        try:
            face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
            if face_cascade.empty():
                logging.warning("Failed to load Haar Cascade. Face detection disabled.")
                face_cascade = None
        except Exception as e:
            logging.warning(f"Error loading Haar Cascade: {e}")
            face_cascade = None

        cap = self.get_camera()
        if not cap and face_cascade:
             logging.warning("Could not open camera for standby monitoring.")
        
        start_time = time.time()
        face_frames = 0
        REQUIRED_FACE_FRAMES = 30 # Increased to prevent "instant" loops. Requires ~1s of sustained face detection.
        
        while time.time() - start_time < duration:
            # 1. Check Interrupts
            if check_interrupt and check_interrupt():
                if cap: cap.release()
                return 'INTERRUPT'
            
            # 2. Check Exit (ESC)
            if self.check_for_exit():
                if cap: cap.release()
                pass # check_active should catch exit if main loop handles it, or we treat as interrupt?
                # Actually check_active usually checks events. 
                # check_for_exit returns true if ESC pressed. 
                # We should probably return INTERRUPT so main loop can handle exit.
                return 'INTERRUPT' 

            # 3. Face Detection
            if cap and face_cascade:
                ret, frame = cap.read()
                if ret:
                    # PROACTIVE FIX: Rotate frame for face detection matching recording settings
                    frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)

                    # Resize for speed?
                    small_frame = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5) 
                    gray = cv2.cvtColor(small_frame, cv2.COLOR_BGR2GRAY)
                    
                    faces = face_cascade.detectMultiScale(
                        gray,
                        scaleFactor=1.3,
                        minNeighbors=5,
                        minSize=(30, 30)
                    )
                    
                    if len(faces) > 0:
                        face_frames += 1
                        # logging.debug(f"Face detected! Count: {face_frames}")
                    else:
                        face_frames = 0
                    
                    if face_frames >= REQUIRED_FACE_FRAMES:
                        logging.info("Face detected! Triggering Standby Video.")
                        cap.release()
                        return 'FACE'
            
            # 4. Wait/Sleep
            # We call waitKey to keep window processed (even if we are showing static image)
            # check_for_exit called waitKey(10), so we are good.
            # But let's sleep a bit more to save CPU if no camera
            if not cap:
                time.sleep(0.1)
                
        if cap: cap.release()
        return 'TIMEOUT'

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

                # 3. Focus Instruction (Blinking) - REMOVED AS REQUESTED
                # if int(time.time() * 2) % 2 == 0:
                #    pass

                # 4. Instructions (Bottom Fixed)
                # "Di 'Borrar' para corregir | Di 'Confirmar' para terminar | Di 'Borrar Todo' para reiniciar"
                instr_text = "Di 'Borrar' para corregir  |  Di 'Confirmar' para finalizar  |  Di 'Borrar Todo' para reiniciar"
                font_scale_i = 1.0
                thickness_i = 2
                text_size_i = cv2.getTextSize(instr_text, font, font_scale_i, thickness_i)[0]
                text_x_i = (img.shape[1] - text_size_i[0]) // 2
                text_y_i = (img.shape[0]) - 120
                cv2.putText(img, instr_text, (text_x_i, text_y_i), font, font_scale_i, (200, 200, 200), thickness_i)

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
