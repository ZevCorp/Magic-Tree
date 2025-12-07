import os
import sys
import json
import queue
import threading
import time
import pyaudio
import pygame
from vosk import Model, KaldiRecognizer

# Configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "model", "vosk-model-small-es-0.42")
AUDIO_ASSETS_PATH = os.path.join(BASE_DIR, "assets", "audio")

# Audio Config
SAMPLE_RATE = 16000
CHUNK_SIZE = 4000

class PhoneInputSystem:
    def __init__(self):
        self.running = True
        self.phone_number = []
        self.confirmed = False
        
        # Initialize Pygame Mixer for low latency audio
        pygame.mixer.init()
        self.sounds = self._load_sounds()
        
        # Initialize Vosk
        if not os.path.exists(MODEL_PATH):
            print(f"Model not found at {MODEL_PATH}. Please run setup_experiment.py first.")
            sys.exit(1)
        
        print("Loading model...")
        self.model = Model(MODEL_PATH)
        self.recognizer = KaldiRecognizer(self.model, SAMPLE_RATE)
        print("Model loaded.")
        
        # Audio Queue
        self.audio_queue = queue.Queue()
        
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
            # Tens (Simple mapping, might cause issues with 'y' e.g. thirty-one -> 301)
            "treinta": "30", "cuarenta": "40", "cincuenta": "50", "sesenta": "60",
            "setenta": "70", "ochenta": "80", "noventa": "90", "cien": "100"
        }
        
        self.correction_words = ["no", "borrar", "corregir", "atras", "mal"]
        self.confirmation_words = ["si", "confirmar", "ok", "listo", "correcto", "ya"]

    def normalize_text(self, text):
        # Simple accent removal
        replacements = (
            ("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"), ("ú", "u"),
            ("ñ", "n"), ("ü", "u")
        )
        for a, b in replacements:
            text = text.replace(a, b)
        return text

    def _load_sounds(self):
        sounds = {}
        files = os.listdir(AUDIO_ASSETS_PATH)
        for f in files:
            if f.endswith(".mp3"):
                name = os.path.splitext(f)[0]
                path = os.path.join(AUDIO_ASSETS_PATH, f)
                try:
                    sounds[name] = pygame.mixer.Sound(path)
                except Exception as e:
                    print(f"Error loading sound {f}: {e}")
        return sounds

    def play_sound(self, name):
        if name in self.sounds:
            self.sounds[name].play()
        else:
            print(f"Sound '{name}' not found.")

    def audio_callback(self, in_data, frame_count, time_info, status):
        self.audio_queue.put(in_data)
        return (None, pyaudio.paContinue)

    def process_audio(self):
        p = pyaudio.PyAudio()
        stream = p.open(format=pyaudio.paInt16,
                        channels=1,
                        rate=SAMPLE_RATE,
                        input=True,
                        frames_per_buffer=CHUNK_SIZE,
                        stream_callback=self.audio_callback)
        
        stream.start_stream()
        
        print("Listening... (Speak digits)")
        self.play_sound("intro")
        
        while self.running:
            try:
                data = self.audio_queue.get(timeout=0.5)
                if self.recognizer.AcceptWaveform(data):
                    result = json.loads(self.recognizer.Result())
                    text = result.get("text", "")
                    if text:
                        self.process_text(text)
                else:
                    # Partial results for faster feedback?
                    partial = json.loads(self.recognizer.PartialResult())
                    # We could use partial results but Vosk partials can be unstable.
                    # For digits, full result is usually fast enough if we speak clearly.
                    # Let's stick to full result for stability first, or check partial if needed.
                    pass
                    
            except queue.Empty:
                continue
            except KeyboardInterrupt:
                self.running = False
        
        stream.stop_stream()
        stream.close()
        p.terminate()

    def process_text(self, text):
        text = self.normalize_text(text)
        print(f"Heard (norm): {text}")
        words = text.split()
        
        for word in words:
            # Check for digits
            if word in self.digit_map:
                digits = self.digit_map[word] # e.g. "22"
                
                for digit in digits:
                    if len(self.phone_number) < 10:
                        self.phone_number.append(digit)
                        print(f"Number: {''.join(self.phone_number)}")
                        self.play_sound(digit)
                        
                        if len(self.phone_number) == 10:
                            self.handle_completion()
                            return # Stop processing this chunk to avoid over-filling immediately
            
            # Check for correction
            elif word in self.correction_words:
                if self.phone_number:
                    removed = self.phone_number.pop()
                    print(f"Removed {removed}. Number: {''.join(self.phone_number)}")
                    self.play_sound("borrado")
                    # Optionally say the previous number to confirm where we are
                    if self.phone_number:
                        last = self.phone_number[-1]
                        # self.play_sound(last) # Maybe too chatty?
                else:
                    self.play_sound("que") # "What?" or "Empty"

            # Check for confirmation (only if full)
            elif word in self.confirmation_words:
                if len(self.phone_number) == 10:
                    self.confirmed = True
                    self.play_sound("confirmar")
                    print("CONFIRMED!")
                    self.running = False
                    return

    def handle_completion(self):
        print("10 digits reached. Verifying...")
        time.sleep(0.5)
        # Read full number
        for digit in self.phone_number:
            self.play_sound(digit)
            time.sleep(0.6) # Pause between digits
        
        print("Waiting for confirmation...")
        # We continue loop to wait for 'confirmar' or 'no'

if __name__ == "__main__":
    system = PhoneInputSystem()
    try:
        system.process_audio()
    except KeyboardInterrupt:
        print("\nExiting...")
