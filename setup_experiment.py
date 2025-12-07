import os
import sys
import zipfile
import urllib.request
import requests
import time

# Configuration
MODEL_URL = "https://alphacephei.com/vosk/models/vosk-model-small-es-0.42.zip"
MODEL_ZIP_NAME = "vosk-model-small-es-0.42.zip"
MODEL_DIR_NAME = "vosk-model-small-es-0.42"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "model")
AUDIO_ASSETS_PATH = os.path.join(BASE_DIR, "assets", "audio")

def download_model():
    if not os.path.exists(MODEL_PATH):
        os.makedirs(MODEL_PATH)
    
    final_model_path = os.path.join(MODEL_PATH, MODEL_DIR_NAME)
    if os.path.exists(final_model_path):
        print(f"Model already exists at {final_model_path}")
        return

    zip_path = os.path.join(MODEL_PATH, MODEL_ZIP_NAME)
    
    print(f"Downloading model from {MODEL_URL}...")
    urllib.request.urlretrieve(MODEL_URL, zip_path)
    print("Download complete.")

    print("Extracting model...")
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(MODEL_PATH)
    print("Extraction complete.")
    
    # Cleanup zip
    os.remove(zip_path)

def generate_audio_assets():
    if not os.path.exists(AUDIO_ASSETS_PATH):
        os.makedirs(AUDIO_ASSETS_PATH)
    
    # Text to generate
    texts = {
        "0": "cero",
        "1": "uno",
        "2": "dos",
        "3": "tres",
        "4": "cuatro",
        "5": "cinco",
        "6": "seis",
        "7": "siete",
        "8": "ocho",
        "9": "nueve",
        "que": "qué?",
        "confirmar": "número confirmado",
        "borrado": "borrado",
        "intro": "Por favor, dicta tu número de teléfono."
    }

    print("Generating audio assets...")
    
    # Try using gTTS first (online), fallback to system if needed? 
    # Actually, for consistency and quality, let's try to use gTTS if available, 
    # or a simple online TTS API to get MP3s.
    # Using gTTS library if installed, otherwise we can use a simple request to google translate api unofficial or similar,
    # BUT to be robust and "local" friendly, let's assume we might not have gTTS installed.
    # Let's try to install gTTS if missing or use a simple hack.
    
    try:
        from gtts import gTTS
        for key, text in texts.items():
            filename = os.path.join(AUDIO_ASSETS_PATH, f"{key}.mp3")
            if not os.path.exists(filename):
                print(f"Generating {filename}...")
                tts = gTTS(text=text, lang='es')
                tts.save(filename)
                time.sleep(0.2) # be nice to API
    except ImportError:
        print("gTTS not found. Installing...")
        os.system(f"{sys.executable} -m pip install gTTS")
        from gtts import gTTS
        for key, text in texts.items():
            filename = os.path.join(AUDIO_ASSETS_PATH, f"{key}.mp3")
            if not os.path.exists(filename):
                print(f"Generating {filename}...")
                tts = gTTS(text=text, lang='es')
                tts.save(filename)
                time.sleep(0.2)

    print("Audio assets generated.")

if __name__ == "__main__":
    download_model()
    generate_audio_assets()
