import cv2
import time
import logging
import os
import threading
import numpy as np
import subprocess
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
                    logging.error("VLC Error detected!")
                    try:
                        # Attempt to stop player first
                        self.player.stop()
                    except:
                        pass
                    
                    logging.critical("CRITICAL: Video playback failed due to hardware/codec state.")
                    logging.critical("Initiating SYSTEM REBOOT in 5 seconds to recover...")
                    time.sleep(5)
                    os.system("sudo reboot")
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
        """
        Records video using FFmpeg with LIVE PREVIEW via v4l2loopback.
        FFmpeg sends video to both file and virtual camera /dev/video10.
        OpenCV reads from virtual camera to show real-time preview.
        """
        logging.info(f"Starting FFMPEG recording with LIVE PREVIEW to {output_path}")
        
        # Find camera device
        video_device = None
        for i in range(4):
            dev = f"/dev/video{i}"
            if os.path.exists(dev):
                video_device = dev
                break
        
        if not video_device:
            logging.error("Could not find video device")
            return
            
        logging.info(f"Using video device: {video_device}")
        
        # Virtual camera for preview
        preview_device = "/dev/video10"
        preview_available = os.path.exists(preview_device)
        
        if not preview_available:
            logging.warning(f"Preview device {preview_device} not found. Recording without preview.")
        
        duration = 20
        final_output = output_path.replace(".avi", ".mp4")
        
        if preview_available:
            # FFmpeg with split: one to file, one to virtual camera for preview
            # Using filter_complex to split video after transpose
            cmd = [
                'ffmpeg',
                '-y',
                '-f', 'v4l2',
                '-video_size', '1280x720',
                '-framerate', '30',
                '-input_format', 'mjpeg',
                '-i', video_device,
                '-f', 'pulse',
                '-ac', '1',
                '-i', 'default',
                '-t', str(duration),
                '-filter_complex', '[0:v]transpose=1,split=2[rec][prev]',
                # Output 1: Recording to file
                '-map', '[rec]',
                '-map', '1:a',
                '-c:v', 'libx264',
                '-preset', 'ultrafast',
                '-crf', '25',
                '-c:a', 'aac',
                '-b:a', '128k',
                '-pix_fmt', 'yuv420p',
                '-movflags', '+faststart',
                final_output,
                # Output 2: Preview to virtual camera
                '-map', '[prev]',
                '-f', 'v4l2',
                '-pix_fmt', 'yuv420p',
                preview_device
            ]
        else:
            # Fallback: original command without preview
            cmd = [
                'ffmpeg',
                '-y',
                '-f', 'v4l2',
                '-video_size', '1280x720',
                '-framerate', '30',
                '-input_format', 'mjpeg',
                '-i', video_device,
                '-f', 'pulse',
                '-ac', '1',
                '-i', 'default',
                '-t', str(duration),
                '-c:v', 'libx264',
                '-preset', 'ultrafast',
                '-crf', '25',
                '-vf', 'transpose=1',
                '-c:a', 'aac',
                '-b:a', '128k',
                '-pix_fmt', 'yuv420p',
                '-movflags', '+faststart',
                final_output
            ]
        
        logging.info(f"FFmpeg Command: {' '.join(cmd)}")
        
        # Start FFmpeg
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        start_time = time.time()
        
        # Open virtual camera for preview if available (with retries)
        preview_cap = None
        if preview_available:
            # Give FFmpeg more time to initialize and start writing to virtual cam
            time.sleep(1.5)
            
            # Try multiple times to open the preview device
            for attempt in range(5):
                logging.info(f"Attempting to open preview device (attempt {attempt + 1}/5)...")
                preview_cap = cv2.VideoCapture(preview_device)
                if preview_cap.isOpened():
                    # Try to read a test frame
                    ret, test_frame = preview_cap.read()
                    if ret and test_frame is not None:
                        logging.info(f"Preview device opened successfully! Frame shape: {test_frame.shape}")
                        break
                    else:
                        preview_cap.release()
                        preview_cap = None
                else:
                    preview_cap = None
                
                if preview_cap is None:
                    time.sleep(0.5)  # Wait before retry
            
            if preview_cap is None:
                logging.warning("Could not open preview device after 5 attempts, falling back to countdown only")
        
        # Show preview with overlay while recording
        try:
            while proc.poll() is None:
                elapsed = time.time() - start_time
                remaining = max(0, int(duration - elapsed))
                
                # Try to get preview frame
                preview_frame = None
                if preview_cap:
                    ret, preview_frame = preview_cap.read()
                    if not ret or preview_frame is None:
                        preview_frame = None
                
                # Create base frame (black background at screen resolution)
                frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
                
                if preview_frame is not None:
                    # Maintain aspect ratio: fit vertical video (720x1280) into 1920x1080 screen
                    # Video is 720w x 1280h (9:16 vertical)
                    # Screen is 1920w x 1080h (16:9 horizontal)
                    # Scale video to fit height (1080), width will be 720 * (1080/1280) = 607.5
                    src_h, src_w = preview_frame.shape[:2]
                    
                    # Calculate scaling to fit within screen while maintaining aspect ratio
                    scale = min(1920 / src_w, 1080 / src_h)
                    new_w = int(src_w * scale)
                    new_h = int(src_h * scale)
                    
                    # Resize video maintaining aspect ratio
                    resized = cv2.resize(preview_frame, (new_w, new_h))
                    
                    # Center the video on the black background
                    x_offset = (1920 - new_w) // 2
                    y_offset = (1080 - new_h) // 2
                    
                    # Place the resized video on the black frame
                    frame[y_offset:y_offset+new_h, x_offset:x_offset+new_w] = resized
                
                # Add overlay: Recording indicator (red circle with pulse effect)
                pulse = int(15 * abs(np.sin(time.time() * 3)))  # Pulsing effect
                cv2.circle(frame, (100, 80), 25 + pulse, (0, 0, 255), -1)
                
                # "REC" text
                cv2.putText(frame, "REC", (140, 95), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 3)
                
                # Countdown in bottom right
                countdown_text = str(remaining)
                cv2.putText(frame, countdown_text, (1750, 1030), 
                           cv2.FONT_HERSHEY_SIMPLEX, 3, (255, 255, 255), 6)
                
                cv2.imshow(WINDOW_NAME, frame)
                cv2.waitKey(33)  # ~30fps preview
                
                if remaining <= 0:
                    break
                    
        except Exception as e:
            logging.error(f"Preview display error: {e}")
        
        # Cleanup preview
        if preview_cap:
            preview_cap.release()
        
        # Wait for FFmpeg to finish
        try:
            stdout, stderr = proc.communicate(timeout=10)
            if proc.returncode != 0:
                logging.warning(f"FFmpeg exit code: {proc.returncode}")
                logging.debug(f"FFmpeg stderr: {stderr.decode() if stderr else 'none'}")
        except subprocess.TimeoutExpired:
            proc.terminate()
            proc.wait()
            logging.warning("FFmpeg terminated due to timeout")
            
        self.show_black_screen()
        logging.info("Recording finished.")

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
