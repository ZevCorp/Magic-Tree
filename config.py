import os

# Hardware Configuration
DOOR_SENSOR_PIN = 17  # GPIO Pin for the door sensor

# API Configuration
import os

# Hardware Configuration
DOOR_SENSOR_PIN = 17  # GPIO Pin for the door sensor

# API Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "YOUR_OPENAI_API_KEY") # Replace with your actual API key

# File Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
RECORDINGS_DIR = os.path.join(BASE_DIR, "recordings")
MODEL_DIR = os.path.join(BASE_DIR, "model")

INTRO_VIDEO_PATH = os.path.join(ASSETS_DIR, "intro.mp4")
INTRO_VIDEO_2_PATH = os.path.join(ASSETS_DIR, "intro_2.mp4")
ASK_PHONE_VIDEO_PATH = os.path.join(ASSETS_DIR, "ask_phone.mp4")
CHRISTMAS_BG_PATH = os.path.join(ASSETS_DIR, "christmas_bg.png")
BACKGROUND_MUSIC_PATH = os.path.join(ASSETS_DIR, "background_music.mp3")

# Audio Configuration
SAMPLE_RATE = 16000
CHANNELS = 1
CHUNK_SIZE = 8000
VOSK_MODEL_PATH = os.path.join(MODEL_DIR, "vosk-model-small-es-0.42") # Example model name

# Messaging Configuration
PHONE_COUNTRY_CODE = "57" # Colombia

# Ensure directories exist
os.makedirs(ASSETS_DIR, exist_ok=True)
os.makedirs(RECORDINGS_DIR, exist_ok=True)
os.makedirs(MODEL_DIR, exist_ok=True)
