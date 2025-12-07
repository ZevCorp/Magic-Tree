import os
import queue
import threading
import time
import pygame
from openai import OpenAI
import tempfile

class TTSManager:
    def __init__(self, api_key=None):
        self.queue = queue.Queue()
        self.running = True
        self.client = None
        
        # Try to initialize OpenAI client
        if api_key:
            self.client = OpenAI(api_key=api_key)
        elif os.environ.get("OPENAI_API_KEY"):
            self.client = OpenAI()
        else:
            print("Warning: No OpenAI API Key found. TTS will not work for dynamic text.")
            
        # Start worker thread
        self.worker_thread = threading.Thread(target=self._worker, daemon=True)
        self.worker_thread.start()

    def speak(self, text):
        """Add text to the speech queue."""
        if not text:
            return
        self.queue.put(text)

    def _worker(self):
        while self.running:
            try:
                text = self.queue.get(timeout=0.5)
                self._process_speech(text)
                self.queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Error in TTS worker: {e}")

    def _process_speech(self, text):
        if not self.client:
            print(f"TTS (No Client): {text}")
            return

        try:
            # Generate speech
            response = self.client.audio.speech.create(
                model="tts-1",
                voice="alloy", # or 'nova', 'shimmer'
                input=text
            )
            
            # Save to temp file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
                for chunk in response.iter_bytes():
                    tmp.write(chunk)
                tmp_path = tmp.name

            # Play audio
            try:
                # We use pygame mixer music or sound. 
                # Sound is better for short clips, Music for longer.
                # Sound loads fully into memory.
                sound = pygame.mixer.Sound(tmp_path)
                channel = sound.play()
                
                # Wait for playback to finish
                while channel.get_busy():
                    time.sleep(0.1)
                    
            finally:
                # Cleanup
                try:
                    os.remove(tmp_path)
                except:
                    pass
                    
        except Exception as e:
            print(f"TTS Error: {e}")

    def stop(self):
        self.running = False
        if self.worker_thread.is_alive():
            self.worker_thread.join(timeout=1.0)
