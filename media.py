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

    def record_user(self, output_path, stop_event):
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

        logging.info("Recording started! Waiting for 'Feliz Navidad' or 'q' key...")
        frame_count = 0
        
        while not stop_event.is_set():
            ret, frame = self.camera.read()
            if ret:
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

class PhoneDisplay(threading.Thread):
    def __init__(self):
        super().__init__()
        self.number = ""
        self.status = "Escuchando..."
        self.running = True
        self.lock = threading.Lock()
        self.window_name = "Phone Verification"
        
    def run(self):
        try:
            logging.info("PhoneDisplay thread started")
            import numpy as np
            from config import CHRISTMAS_BG_PATH
            
            logging.info(f"Creating window: {self.window_name}")
            cv2.namedWindow(self.window_name, cv2.WND_PROP_FULLSCREEN)
            cv2.setWindowProperty(self.window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
            logging.info("Window created and set to fullscreen")
            
            # Load Background
            if os.path.exists(CHRISTMAS_BG_PATH):
                logging.info(f"Loading Christmas background from {CHRISTMAS_BG_PATH}")
                bg_img = cv2.imread(CHRISTMAS_BG_PATH)
                bg_img = cv2.resize(bg_img, (1920, 1080))
                logging.info("Background loaded successfully")
            else:
                logging.warning(f"Christmas background not found at {CHRISTMAS_BG_PATH}, using black.")
                bg_img = np.zeros((1080, 1920, 3), dtype=np.uint8)

            font = cv2.FONT_HERSHEY_SIMPLEX
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
                
                if cv2.waitKey(100) & 0xFF == ord('q'):
                    self.running = False
            
            logging.info("PhoneDisplay loop ended, destroying window")
            cv2.destroyWindow(self.window_name)
            logging.info("PhoneDisplay thread finished")
            
        except Exception as e:
            logging.error(f"Error in PhoneDisplay thread: {e}", exc_info=True)

    def update_number(self, number):
        with self.lock:
            self.number = number

    def set_status(self, status):
        with self.lock:
            self.status = status

    def stop(self):
        self.running = False
        self.join()
