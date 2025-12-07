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

try:
    from faster_whisper import WhisperModel
    FASTER_WHISPER_AVAILABLE = True
except ImportError:
    FASTER_WHISPER_AVAILABLE = False
    logging.warning("faster-whisper not found. Local transcription will be disabled.")

try:
    import pyttsx3
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False
    logging.warning("pyttsx3 not found. Text-to-speech will be disabled.")

def extract_digits_from_text(text):
    """
    Extracts digits from text, converting Spanish number words to digits.
    """
    if not text:
        return ""
        
    text = text.lower()
    
    # Map Spanish number words to digits
    number_map = {
        "cero": "0", "uno": "1", "una": "1", "dos": "2", "tres": "3", "cuatro": "4",
        "cinco": "5", "seis": "6", "siete": "7", "ocho": "8", "nueve": "9",
        "diez": "10", "once": "11", "doce": "12", "trece": "13", "catorce": "14", "quince": "15"
    }
    
    # Replace words with digits
    for word, digit in number_map.items():
        text = text.replace(word, digit)
        
    # Extract all digits
    digits = re.findall(r'\d', text)
    return "".join(digits)

class LocalSpeechEngine:
    def __init__(self, model_size="tiny", device="cpu", compute_type="int8"):
        self.model = None
        if FASTER_WHISPER_AVAILABLE:
            try:
                logging.info(f"Loading faster-whisper model: {model_size} on {device}...")
                self.model = WhisperModel(model_size, device=device, compute_type=compute_type)
                logging.info("faster-whisper model loaded.")
            except Exception as e:
                logging.error(f"Error loading faster-whisper: {e}")

    def transcribe(self, audio_path):
        if not self.model:
            logging.warning("Local speech engine not available.")
            return ""
            
        try:
            segments, info = self.model.transcribe(audio_path, beam_size=5, language="es")
            text = " ".join([segment.text for segment in segments])
            logging.info(f"Local transcription: {text}")
            return text
        except Exception as e:
            logging.error(f"Error in local transcription: {e}")
            return ""

class TextToSpeech:
    def __init__(self):
        self.engine = None
        if TTS_AVAILABLE:
            try:
                self.engine = pyttsx3.init()
                # Configure voice (try to find Spanish)
                voices = self.engine.getProperty('voices')
                for voice in voices:
                    if "spanish" in voice.name.lower() or "es" in voice.id.lower():
                        self.engine.setProperty('voice', voice.id)
                        break
                self.engine.setProperty('rate', 150) # Speed
            except Exception as e:
                logging.error(f"Error initializing TTS: {e}")

    def speak(self, text):
        if self.engine:
            try:
                logging.info(f"Speaking: {text}")
                self.engine.say(text)
                self.engine.runAndWait()
            except Exception as e:
                logging.error(f"Error in TTS speak: {e}")

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
        
        # Initialize Local Speech Engine
        self.local_speech = LocalSpeechEngine()
        
        # Initialize TTS
        self.tts = TextToSpeech()

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
                    {"role": "system", "content": "You are a helpful assistant that extracts phone numbers from dictated text. Users may dictate numbers in various formats:\n- Individual digits: '3, 11, 8, 22, 43, 56' should become '31182243566' (each number represents its digits)\n- Separated by spaces: '3 1 1 8 2 2 4 3 5 6'\n- Words: 'tres uno uno ocho dos dos cuatro tres cinco seis'\n- Mixed formats with corrections: '555 123 no wait 124'\n\nYour task:\n1. Convert ALL spoken numbers to their digit equivalents (e.g., '11' = '1' and '1', '22' = '2' and '2')\n2. Handle corrections (take the final version)\n3. Output ONLY the final phone number as a continuous sequence of digits\n4. If no valid phone number can be extracted, output nothing"},
                    {"role": "user", "content": f"Extract the phone number from this dictated text: \"{text}\""}
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
