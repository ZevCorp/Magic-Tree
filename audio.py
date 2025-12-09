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
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        
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

    def listen_for_keyword(self, confirm_event, keyword="confirmar"):
        """
        Listens exclusively for a keyword to trigger the event.
        Uses OpenAI for transcription for simplicity/consistency.
        """
        logging.info(f"Listening for keyword: {keyword}")
        
        # We reuse the streaming logic but with local stop event
        local_stop = threading.Event()
        
        # We need to process chunks until keyword is found or global flow stops?
        # Actually this runs in a thread. We should check if confirm_event is set elsewhere too?
        # No, this sets the confirm_event.
        
        for chunk_path in self.stream_audio_chunks(local_stop, chunk_duration=3):
            if confirm_event.is_set():
                break

            text = self.transcribe_with_openai(chunk_path)
            if text:
                logging.info(f"Keyword listener heard: {text}")
                if keyword.lower() in text.lower():
                    logging.info(f"Keyword '{keyword}' detected!")
                    confirm_event.set()
                    local_stop.set()
                    break
            
            try:
                os.remove(chunk_path)
            except:
                pass
                
    def __del__(self):
        if self.p:
            self.p.terminate()
