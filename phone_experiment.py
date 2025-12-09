import os
import sys
import json
import queue
import threading
import time
import pyaudio
import pygame
from vosk import Model, KaldiRecognizer
from openai import OpenAI
from tts_manager import TTSManager

# Configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "model", "vosk-model-small-es-0.42")
AUDIO_ASSETS_PATH = os.path.join(BASE_DIR, "assets", "audio")

# Audio Config
SAMPLE_RATE = 16000
CHUNK_SIZE = 4000
DEVICE_INDEX = None  # Set this to the index of your microphone (e.g., 0, 1, 2)

def list_audio_devices():
    p = pyaudio.PyAudio()
    info = p.get_host_api_info_by_index(0)
    numdevices = info.get('deviceCount')
    
    print("\n--- Available Audio Input Devices ---")
    for i in range(0, numdevices):
        if (p.get_device_info_by_host_api_device_index(0, i).get('maxInputChannels')) > 0:
            name = p.get_device_info_by_host_api_device_index(0, i).get('name')
            print(f"Device ID {i}: {name}")
    print("-------------------------------------\n")
    p.terminate()

class PhoneInputSystem:
    def __init__(self):
        list_audio_devices()
        self.running = True
        self.phone_number = []
        self.confirmed = False
        self.verifying = False
        
        # Initialize Pygame Mixer for low latency audio
        pygame.mixer.init()
        # self.sounds = self._load_sounds() # Removed in favor of TTS
        self.sounds = {} # Keep empty or load specific if needed
        # We might want to load "intro", "que", "borrado", "confirmar" if we use play_sound for them
        # For now, let's assume play_sound handles missing sounds gracefully (it prints error)
        # We should probably load the basic sounds if they exist
        self._load_basic_sounds()

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
        
        # Initialize TTS
        api_key = os.environ.get("OPENAI_API_KEY")
        self.tts = TTSManager(api_key=api_key)
        if api_key:
            self.openai_client = OpenAI(api_key=api_key)
        else:
            print("Warning: No OpenAI API Key found. Confirmation will be limited.")
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

    def _load_basic_sounds(self):
        # Load only essential SFX
        for name in ["intro", "borrado", "que", "confirmar"]:
            path = os.path.join(AUDIO_ASSETS_PATH, f"{name}.mp3")
            if os.path.exists(path):
                try:
                    self.sounds[name] = pygame.mixer.Sound(path)
                except:
                    pass

    def play_sound(self, name):
        if name in self.sounds:
            self.sounds[name].play()
        # else: ignore or print

    def audio_callback(self, in_data, frame_count, time_info, status):
        self.audio_queue.put(in_data)
        return (None, pyaudio.paContinue)

    def process_audio(self):
        p = pyaudio.PyAudio()
        stream = p.open(format=pyaudio.paInt16,
                        channels=1,
                        rate=SAMPLE_RATE,
                        input=True,
                        input_device_index=DEVICE_INDEX,
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
                    pass
                    
            except queue.Empty:
                continue
            except KeyboardInterrupt:
                self.running = False
        
        stream.stop_stream()
        stream.close()
        p.terminate()
        self.tts.stop()

    def process_text(self, text):
        text = self.normalize_text(text)
        print(f"Heard (norm): {text}")
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
                    print(f"Number: {''.join(self.phone_number)}")

            # Check for correction
            elif word in self.correction_words:
                if self.phone_number:
                    removed = self.phone_number.pop()
                    print(f"Removed {removed}. Number: {''.join(self.phone_number)}")
                    self.play_sound("borrado")
                    self.verifying = False # Reset verification if we correct
                else:
                    self.play_sound("que")

            # Check for confirmation (only if full)
            elif word in self.confirmation_words:
                if len(self.phone_number) == 10:
                    self.confirmed = True
                    self.play_sound("confirmar")
                    print("CONFIRMED!")
                    self.running = False
                    return

        # Speak the chunk of numbers found
        if current_chunk_words:
            phrase = " ".join(current_chunk_words)
            self.tts.speak(phrase)

        # Check completion
        if len(self.phone_number) == 10 and not self.confirmed:
            if not self.verifying:
                self.handle_completion()

    def handle_completion(self):
        self.verifying = True
        full_number = "".join(self.phone_number)
        print(f"10 digits reached: {full_number}. Verifying...")
        
        # Use GPT-4o-mini for confirmation
        if self.openai_client:
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
            except Exception as e:
                print(f"OpenAI Error: {e}")
                self.tts.speak(f"El número es {full_number}. ¿Es correcto?")
        else:
            self.tts.speak(f"El número es {full_number}. ¿Es correcto?")
            
        print("Waiting for confirmation...")


if __name__ == "__main__":
    system = PhoneInputSystem()
    try:
        system.process_audio()
    except KeyboardInterrupt:
        print("\nExiting...")
