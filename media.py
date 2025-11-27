import cv2
import time
import logging
import os
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
            self.player.stop() # Ensure it's stopped/closed
        else:
            logging.info("Mock playing video (3 seconds)...")
            time.sleep(3)

    def record_user(self, output_path, stop_event):
        logging.info(f"Starting recording to {output_path}")
        self.camera = cv2.VideoCapture(0)
        if not self.camera.isOpened():
            logging.error("Could not open camera")
            return

        # Define codec and create VideoWriter object
        # XVID is usually safe, or H264 if available
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        width = int(self.camera.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = 20.0 # Adjust based on camera
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

        cv2.namedWindow("Recording", cv2.WND_PROP_FULLSCREEN)
        cv2.setWindowProperty("Recording", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

        while not stop_event.is_set():
            ret, frame = self.camera.read()
            if ret:
                out.write(frame)
                cv2.imshow('Recording', frame)
                
                # Check for 'q' key as manual fallback
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
            else:
                break

        logging.info("Stopping recording...")
        self.camera.release()
        out.release()
        cv2.destroyAllWindows()
