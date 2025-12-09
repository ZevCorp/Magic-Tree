import os
import sys
import json
import queue
import threading
import time
import logging
import pyaudio
import pygame
from vosk import Model, KaldiRecognizer
from openai import OpenAI
from tts_manager import TTSManager
from config import *

# Audio Config
SAMPLE_RATE = 16000
CHUNK_SIZE = 4000
DEVICE_INDEX = None  # Auto-detect default

class PhoneInputSystem:
    def __init__(self, callback_fn=None):
        """
        Initialize the PhoneInputSystem.
        :param callback_fn: A function that takes (number_string, status_string) to update external UI.
        """
        self.callback_fn = callback_fn
        self.running = True
        self.phone_number = []
        self.confirmed = False
        self.verifying = False
        
        # Initialize Pygame Mixer for SFX
        try:
            pygame.mixer.init()
        except Exception as e:
            logging.warning(f"Pygame mixer init failed: {e}")

        self.sounds = {} 
        self._load_basic_sounds()

        # Initialize Vosk
        if not os.path.exists(VOSK_MODEL_PATH):
            logging.error(f"Vosk Model not found at {VOSK_MODEL_PATH}")
            # Fallback or exit? For now, we log error.
        else:
            logging.info(f"Loading Vosk model from {VOSK_MODEL_PATH}...")
            self.model = Model(VOSK_MODEL_PATH)
            self.recognizer = KaldiRecognizer(self.model, SAMPLE_RATE)
            logging.info("Vosk model loaded.")
        
        # Audio Queue
        self.audio_queue = queue.Queue()
        
        # Initialize TTS
        self.tts = TTSManager(api_key=OPENAI_API_KEY)
        if OPENAI_API_KEY and OPENAI_API_KEY != "YOUR_OPENAI_API_KEY":
            self.openai_client = OpenAI(api_key=OPENAI_API_KEY)
        else:
            logging.warning("No valid OpenAI API Key found. Confirmation will be limited.")
            self.openai_client = None
        
        # Word mapping
        self.digit_map = {
            "cero": "0", "uno": "1", "una": "1", "dos": "2", "tres": "3",
            "cuatro": "4", "cinco": "5", "seis": "6", "siete": "7",
            "ocho": "8", "nueve": "9",
            # 10-19
            "diez": "10", "once": "11", "doce": "12", "trece": "13", "catorce": "14", 
            "quince": "15", "dieciseis": "16", "diecisiete": "17", "dieciocho": "18", "diecinueve": "19",
            # 20-29
            "veinte": "20", "veintiuno": "21", "veintidos": "22", "veintitres": "23", "veinticuatro": "24",
            "veinticinco": "25", "veintiseis": "26", "veintisiete": "27", "veintiocho": "28", "veintinueve": "29",
            # Tens
            "treinta": "30", "cuarenta": "40", "cincuenta": "50", "sesenta": "60",
            "setenta": "70", "ochenta": "80", "noventa": "90", "cien": "100"
        }
        
        self.correction_words = ["no", "borrar", "corregir", "atras", "mal"]
        self.confirmation_words = ["si", "confirmar", "ok", "listo", "correcto", "ya"]

    def normalize_text(self, text):
        replacements = (
            ("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"), ("ú", "u"),
            ("ñ", "n"), ("ü", "u")
        )
        for a, b in replacements:
            text = text.replace(a, b)
        return text

    def _load_basic_sounds(self):
        # We assume assets/audio/ exists based on config or parallel folder
        audio_dir = os.path.join(ASSETS_DIR, "audio")
        for name in ["intro", "borrado", "que", "confirmar"]:
            path = os.path.join(audio_dir, f"{name}.mp3")
            if os.path.exists(path):
                try:
                    self.sounds[name] = pygame.mixer.Sound(path)
                except Exception as e:
                    logging.warning(f"Could not load sound {path}: {e}")

    def play_sound(self, name):
        if name in self.sounds:
            try:
                self.sounds[name].play()
            except:
                pass

    def audio_callback(self, in_data, frame_count, time_info, status):
        self.audio_queue.put(in_data)
        return (None, pyaudio.paContinue)

    def start_processing(self):
        """
        Main loop for audio processing. blocking until confirmed or stopped.
        """
        p = pyaudio.PyAudio()
        stream = p.open(format=pyaudio.paInt16,
                        channels=1,
                        rate=SAMPLE_RATE,
                        input=True,
                        input_device_index=DEVICE_INDEX,
                        frames_per_buffer=CHUNK_SIZE,
                        stream_callback=self.audio_callback)
        
        stream.start_stream()
        
        logging.info("PhoneInputSystem: Listening...")
        self.update_ui("Escuchando...")
        self.play_sound("intro")
        
        while self.running:
            try:
                # Non-blocking get with timeout to allow checking self.running
                data = self.audio_queue.get(timeout=0.5)
                if self.recognizer.AcceptWaveform(data):
                    result = json.loads(self.recognizer.Result())
                    text = result.get("text", "")
                    if text:
                        self.process_text(text)
                else:
                    # Partial result if needed, but usually we wait for full blocks
                    pass
                    
            except queue.Empty:
                continue
            except KeyboardInterrupt:
                self.running = False
                break
            except Exception as e:
                logging.error(f"Error in audio loop: {e}")
                
        stream.stop_stream()
        stream.close()
        p.terminate()
        self.tts.stop()
        return "".join(self.phone_number) if self.confirmed else None

    def process_text(self, text):
        text = self.normalize_text(text)
        logging.info(f"Heard: {text}")
        words = text.split()
        
        current_chunk_words = []
        
        for word in words:
            # Check for digits
            if word in self.digit_map:
                digits = self.digit_map[word]
                
                added_any = False
                for digit in digits:
                    if len(self.phone_number) < 10:
                        self.phone_number.append(digit)
                        added_any = True
                
                if added_any:
                    current_chunk_words.append(word)
                    self.update_ui()

            # Check for correction
            elif word in self.correction_words:
                if self.phone_number:
                    removed = self.phone_number.pop()
                    logging.info(f"Removed {removed}")
                    self.play_sound("borrado")
                    self.verifying = False 
                    self.update_ui()
                else:
                    self.play_sound("que")

            # Check for confirmation
            elif word in self.confirmation_words:
                if len(self.phone_number) == 10:
                    self.confirmed = True
                    self.play_sound("confirmar")
                    logging.info("CONFIRMED!")
                    self.running = False
                    return

        # Speak digits found
        if current_chunk_words:
            phrase = " ".join(current_chunk_words)
            self.tts.speak(phrase)

        # Check completion
        if len(self.phone_number) == 10 and not self.confirmed and not self.verifying:
            self.handle_completion()

    def handle_completion(self):
        self.verifying = True
        full_number = "".join(self.phone_number)
        logging.info(f"10 digits reached: {full_number}. Verifying...")
        self.update_ui("Confirmar?")
        
        # Use GPT-4o-mini for confirmation
        if self.openai_client:
            try:
                # We spawn a thread to not block the audio loop? 
                # Actually TTS is threaded, but API call is blocking.
                # Let's do it in a thread briefly or just accept the block (latency might be issue)
                threading.Thread(target=self._generate_confirm_speech, args=(full_number,)).start()
            except Exception as e:
                logging.error(f"OpenAI Error: {e}")
                self.tts.speak(f"El número es {full_number}. ¿Es correcto?")
        else:
            self.tts.speak(f"El número es {full_number}. ¿Es correcto?")
            
    def _generate_confirm_speech(self, full_number):
        try:
             response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant confirming a phone number. Speak naturally in Spanish. Keep it brief. Example: 'Entendido, el número es 311... ¿Es correcto?'"},
                    {"role": "user", "content": f"The user just dictated the phone number {full_number}. Ask them to confirm if it is correct."}
                ]
            )
             confirmation_text = response.choices[0].message.content
             self.tts.speak(confirmation_text)
        except:
             self.tts.speak(f"El número es {full_number}. ¿Es correcto?")

    def update_ui(self, status=None):
        if self.callback_fn:
            number_str = "".join(self.phone_number)
            self.callback_fn(number_str, status)

    def stop(self):
        self.running = False
