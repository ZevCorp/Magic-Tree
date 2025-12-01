import pyaudio
import wave
import json
import logging
import threading
import requests
import os
import re
import time
import openai
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
        
        # Initialize Pygame for music
        try:
            import pygame
            pygame.mixer.init()
            self.pygame_available = True
        except ImportError:
            logging.warning("pygame not found. Background music will be disabled.")
            self.pygame_available = False

    def play_background_music(self):
        if self.pygame_available and os.path.exists(BACKGROUND_MUSIC_PATH):
            try:
                logging.info(f"Playing background music: {BACKGROUND_MUSIC_PATH}")
                import pygame
                pygame.mixer.music.load(BACKGROUND_MUSIC_PATH)
                pygame.mixer.music.play(-1) # Loop indefinitely
            except Exception as e:
                logging.error(f"Error playing background music: {e}")
        else:
            logging.warning("Cannot play background music (pygame missing or file not found).")

    def stop_background_music(self):
        if self.pygame_available:
            try:
                import pygame
                pygame.mixer.music.fadeout(1000)
                logging.info("Background music stopped.")
            except Exception as e:
                logging.error(f"Error stopping background music: {e}")

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

    def transcribe_with_openai(self, audio_path):
        logging.info("Transcribing audio with OpenAI Whisper...")
        if not os.path.exists(audio_path):
            logging.error("Audio file not found.")
            return ""

        try:
            client = openai.OpenAI(api_key=OPENAI_API_KEY)
            with open(audio_path, "rb") as audio_file:
                transcription = client.audio.transcriptions.create(
                    model="whisper-1", 
                    file=audio_file
                )
            text = transcription.text
            logging.info(f"Transcription received: {text}")
            return text
        except Exception as e:
            logging.error(f"Error transcribing with OpenAI: {e}")
            return ""

    def extract_phone_number_with_assistant(self, text):
        logging.info(f"Extracting phone number from text: {text}")
        try:
            client = openai.OpenAI(api_key=OPENAI_API_KEY)
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that extracts phone numbers from text. The user might correct themselves (e.g., '555 123 no wait 124'). You must output ONLY the final, corrected phone number as a sequence of digits. If no phone number is found, output nothing."},
                    {"role": "user", "content": f"Extract the phone number from this text: \"{text}\""}
                ]
            )
            phone_number = response.choices[0].message.content.strip()
            # Remove any non-digit characters just in case
            phone_number = re.sub(r'\D', '', phone_number)
            
            if phone_number:
                logging.info(f"Extracted Phone Number: {phone_number}")
                return phone_number
            else:
                logging.warning("No phone number found by assistant.")
                return None
        except Exception as e:
            logging.error(f"Error extracting phone number with assistant: {e}")
            return None

    def stream_audio_chunks(self, stop_event, chunk_duration=5):
        """
        Generator that yields paths to temporary WAV files containing audio chunks.
        Records continuously until stop_event is set.
        """
        logging.info("Starting continuous audio streaming...")
        stream = self.p.open(format=pyaudio.paInt16, channels=CHANNELS,
                             rate=SAMPLE_RATE, input=True,
                             frames_per_buffer=CHUNK_SIZE)
        
        chunk_frames = int(SAMPLE_RATE / CHUNK_SIZE * chunk_duration)
        
        try:
            while not stop_event.is_set():
                frames = []
                for _ in range(chunk_frames):
                    if stop_event.is_set():
                        break
                    data = stream.read(CHUNK_SIZE, exception_on_overflow=False)
                    frames.append(data)
                
                if frames:
                    timestamp = int(time.time())
                    chunk_path = os.path.join(RECORDINGS_DIR, f"chunk_{timestamp}.wav")
                    
                    wf = wave.open(chunk_path, 'wb')
                    wf.setnchannels(CHANNELS)
                    wf.setsampwidth(self.p.get_sample_size(pyaudio.paInt16))
                    wf.setframerate(SAMPLE_RATE)
                    wf.writeframes(b''.join(frames))
                    wf.close()
                    
                    yield chunk_path
                    
        except Exception as e:
            logging.error(f"Error in audio streaming: {e}")
        finally:
            stream.stop_stream()
            stream.close()
            logging.info("Audio streaming stopped.")
