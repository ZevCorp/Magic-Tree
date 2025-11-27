import pyaudio
import wave
import json
import logging
import threading
import requests
import os
import re
from config import *

try:
    from vosk import Model, KaldiRecognizer
    VOSK_AVAILABLE = True
except ImportError:
    VOSK_AVAILABLE = False
    logging.warning("Vosk not found. Voice commands will be mocked.")

class AudioManager:
    def __init__(self):
        self.p = pyaudio.PyAudio()
        self.vosk_model = None
        if VOSK_AVAILABLE:
            if os.path.exists(VOSK_MODEL_PATH):
                logging.info(f"Loading Vosk model from {VOSK_MODEL_PATH}")
                self.vosk_model = Model(VOSK_MODEL_PATH)
            else:
                logging.warning(f"Vosk model not found at {VOSK_MODEL_PATH}")

    def listen_for_keyword(self, stop_event, keyword="feliz navidad"):
        """
        Listens for the keyword in a loop. Sets stop_event when found.
        Should be run in a separate thread.
        """
        if not self.vosk_model:
            logging.info("No Vosk model. Waiting 10 seconds then simulating trigger.")
            time.sleep(10)
            stop_event.set()
            return

        rec = KaldiRecognizer(self.vosk_model, SAMPLE_RATE)
        stream = self.p.open(format=pyaudio.paInt16, channels=CHANNELS,
                             rate=SAMPLE_RATE, input=True,
                             frames_per_buffer=CHUNK_SIZE)
        stream.start_stream()

        logging.info(f"Listening for keyword: {keyword}")
        while not stop_event.is_set():
            data = stream.read(CHUNK_SIZE, exception_on_overflow=False)
            if rec.AcceptWaveform(data):
                result = json.loads(rec.Result())
                text = result.get("text", "")
                if keyword in text.lower():
                    logging.info(f"Keyword '{keyword}' detected!")
                    stop_event.set()
                    break
        
        stream.stop_stream()
        stream.close()

    def record_audio(self, output_path, duration=5):
        logging.info(f"Recording audio to {output_path} for {duration} seconds...")
        stream = self.p.open(format=pyaudio.paInt16, channels=CHANNELS,
                             rate=SAMPLE_RATE, input=True,
                             frames_per_buffer=CHUNK_SIZE)
        
        frames = []
        for _ in range(0, int(SAMPLE_RATE / CHUNK_SIZE * duration)):
            data = stream.read(CHUNK_SIZE)
            frames.append(data)
            
        stream.stop_stream()
        stream.close()
        
        wf = wave.open(output_path, 'wb')
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(self.p.get_sample_size(pyaudio.paInt16))
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(b''.join(frames))
        wf.close()
        logging.info("Audio recording complete.")

    def transcribe_with_whisperflow(self, audio_path):
        logging.info("Sending audio to Whisperflow...")
        if not os.path.exists(audio_path):
            logging.error("Audio file not found.")
            return ""

        headers = {"Authorization": f"Bearer {WHISPERFLOW_API_KEY}"}
        # Note: Adjust the request based on actual Whisperflow API docs.
        # Assuming standard multipart/form-data upload.
        try:
            with open(audio_path, 'rb') as f:
                files = {'file': f}
                response = requests.post(WHISPERFLOW_API_URL, headers=headers, files=files)
            
            if response.status_code == 200:
                data = response.json()
                text = data.get("text", "")
                logging.info(f"Transcription received: {text}")
                return text
            else:
                logging.error(f"Whisperflow API Error: {response.status_code} - {response.text}")
                return ""
        except Exception as e:
            logging.error(f"Exception calling Whisperflow: {e}")
            return ""

    def extract_phone_number(self, text):
        # Simple regex for phone numbers (adjust for locale)
        # Looks for sequences of digits
        phone_pattern = re.compile(r'\b\d{7,15}\b') 
        match = phone_pattern.search(text.replace(" ", "").replace("-", ""))
        if match:
            return match.group(0)
        return None
