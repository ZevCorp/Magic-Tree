import os
import time
import wave
import logging
import threading
import json
import re

import pyaudio
import pygame
from openai import OpenAI

from config import *
try:
    from vosk import Model, KaldiRecognizer
    VOSK_AVAILABLE = True
except ImportError:
    logging.warning("Vosk not found. Voice recognition will be disabled.")
    VOSK_AVAILABLE = False

# Initialize Pygame Mixer for background music
try:
    pygame.mixer.init()
    PYGAME_AVAILABLE = True
except Exception as e:
    logging.warning(f"Pygame mixer failed to initialize: {e}")
    PYGAME_AVAILABLE = False

class AudioManager:
    def __init__(self):
        self.chunk = CHUNK_SIZE
        self.format = pyaudio.paInt16
        self.channels = CHANNELS
        self.rate = SAMPLE_RATE
        self.p = pyaudio.PyAudio()
        
        # Initialize OpenAI Client safely
        if not OPENAI_API_KEY or OPENAI_API_KEY == "YOUR_OPENAI_API_KEY":
            logging.critical("OPENAI_API_KEY is missing or default! Voice features will not work.")
            print("\n!!!! ATTENTION !!!!")
            print("Please set your OPENAI_API_KEY in .env file or environment.")
            print("!!!! ATTENTION !!!!\n")
            self.client = None
        else:
            try:
                self.client = OpenAI(api_key=OPENAI_API_KEY)
            except Exception as e:
                logging.error(f"Failed to initialize OpenAI client: {e}")
                logging.error(f"Failed to initialize OpenAI client: {e}")
                self.client = None

        # Initialize Vosk Model
        self.vosk_model = None
        if VOSK_AVAILABLE:
            if os.path.exists(VOSK_MODEL_PATH):
                try:
                    logging.info(f"Loading Vosk model from {VOSK_MODEL_PATH}...")
                    self.vosk_model = Model(VOSK_MODEL_PATH)
                    logging.info("Vosk model loaded successfully.")
                except Exception as e:
                    logging.error(f"Failed to load Vosk model: {e}")
            else:
                logging.warning(f"Vosk model path valid not found: {VOSK_MODEL_PATH}")
        
    def stream_audio_chunks(self, stop_event, chunk_duration=5):
        """
        Generator that records audio in chunks and yields the file path.
        Stops when stop_event is set.
        """
        # Determine strict chunk size based on rate and duration
        frames_per_chunk = int(self.rate * chunk_duration)
        
        logging.info("Starting audio stream...")
        
        stream = self.p.open(format=self.format,
                             channels=self.channels,
                             rate=self.rate,
                             input=True,
                             frames_per_buffer=self.chunk)
        try:                     
            while not stop_event.is_set():
                logging.debug("Recording chunk...")
                frames = []
                
                # Record for chunk_duration
                for _ in range(0, int(self.rate / self.chunk * chunk_duration)):
                    if stop_event.is_set():
                        break
                    try:
                        data = stream.read(self.chunk, exception_on_overflow=False)
                        frames.append(data)
                    except Exception as e:
                        logging.error(f"Error reading audio stream: {e}")
                        
                if not frames:
                    continue
                    
                # Save to temporary file
                timestamp = int(time.time() * 1000)
                filename = os.path.join(RECORDINGS_DIR, f"chunk_{timestamp}.wav")
                
                wf = wave.open(filename, 'wb')
                wf.setnchannels(self.channels)
                wf.setsampwidth(self.p.get_sample_size(self.format))
                wf.setframerate(self.rate)
                wf.writeframes(b''.join(frames))
                wf.close()
                
                yield filename
        finally: 
            logging.info("Stopping audio stream...")
            stream.stop_stream()
            stream.close()

    def transcribe_with_openai(self, audio_path):
        """
        Transcribes the given audio file using OpenAI Whisper API.
        """
        if not os.path.exists(audio_path):
            logging.warning(f"Audio file not found: {audio_path}")
            return None

        if not self.client:
            logging.error("OpenAI client not initialized. Cannot transcribe.")
            return None
            
        try:
            with open(audio_path, "rb") as audio_file:
                transcription = self.client.audio.transcriptions.create(
                    model="whisper-1", 
                    file=audio_file,
                    language="es"
                )
            return transcription.text
        except Exception as e:
            logging.error(f"OpenAI Transcription error: {e}")
            return None

    def extract_phone_number_with_assistant(self, text):
        """
        Extracts a phone number from the accumulated text using GPT.
        Returns the number as a string of digits if found, or None.
        """
        if not text or len(text.strip()) < 5:
            return None

        if not self.client:
            return None
            
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a helper that extracts phone numbers from messy text. Return ONLY the digits of the phone number found (e.g., '3115551234'). If multiple, return the last one. If none, return 'NONE'. Ignore words, just look for a sequence of 10 digits typical in Colombia (starts with 3)."},
                    {"role": "user", "content": f"Extract the phone number from: {text}"}
                ],
                max_tokens=20
            )
            result = response.choices[0].message.content.strip()
            
            # Basic validation
            digits = re.sub(r'\D', '', result)
            if len(digits) >= 10:
                # Colombia specific check (optional): usually starts with 3
                if digits.startswith('3'): 
                    return digits
                else:
                    return digits # Accept anyway for flexibility
            return None
            
        except Exception as e:
            logging.error(f"Extraction error: {e}")
            return None

    def play_background_music(self):
        """
        Plays background music in a loop.
        """
        if not PYGAME_AVAILABLE:
            logging.warning("Pygame not available, cannot play music.")
            return

        if os.path.exists(BACKGROUND_MUSIC_PATH):
            try:
                pygame.mixer.music.load(BACKGROUND_MUSIC_PATH)
                pygame.mixer.music.play(-1) # Loop forever
                pygame.mixer.music.set_volume(0.5)
                logging.info("Background music started.")
            except Exception as e:
                logging.error(f"Error playing music: {e}")
        else:
            logging.warning(f"Music file not found: {BACKGROUND_MUSIC_PATH}")

    def stop_background_music(self):
        """
        Stops the background music.
        """
        if PYGAME_AVAILABLE:
            try:
                pygame.mixer.music.stop()
                logging.info("Background music stopped.")
            except Exception as e:
                logging.error(f"Error stopping music: {e}")

    def listen_for_keyword(self, stop_event, keyword="confirmar"):
        """
        Listens locally using Vosk for a keyword to trigger the event.
        """
        if not self.vosk_model:
            logging.warning("Vosk model not loaded, cannot listen for keyword.")
            return

        logging.info(f"Listening for keyword '{keyword}' (Local Vosk)...")
        
        try:
            rec = KaldiRecognizer(self.vosk_model, self.rate)
            
            stream = self.p.open(format=self.format,
                                 channels=self.channels,
                                 rate=self.rate,
                                 input=True,
                                 frames_per_buffer=4000) # Vosk likes larger chunks usually or small is fine
            
            # Use a slightly smaller chunk for reading to be responsive to stop_event
            read_chunk = 4000
            
            while not stop_event.is_set():
                try:
                    data = stream.read(read_chunk, exception_on_overflow=False)
                    if len(data) == 0:
                        break
                        
                    if rec.AcceptWaveform(data):
                        result = json.loads(rec.Result())
                        text = result.get("text", "")
                        if text:
                            # logging.info(f"Vosk Heard: {text}")
                            if keyword.lower() in text.lower():
                                logging.info(f"Keyword '{keyword}' detected!")
                                stop_event.set()
                                break
                    else:
                        # Partial result (optional to check, but usually we wait for full)
                        pass
                        
                except Exception as e:
                    logging.error(f"Error in keyword listener: {e}")
                    break
            
            stream.stop_stream()
            stream.close()
            logging.info("Keyword listener stopped.")
            
        except Exception as e:
            logging.error(f"Failed to start Vosk stream: {e}")
                
    def __del__(self):
        if self.p:
            self.p.terminate()
