import os
import sys
import json
import queue
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
        if self.tts:
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
            if self.tts:
                self.tts.speak(phrase)

        # Check completion
        if len(self.phone_number) == 10 and not self.confirmed and not self.verifying:
            self.handle_completion()

    def handle_completion(self):
        self.verifying = True
        full_number = "".join(self.phone_number)
        logging.info(f"10 digits reached: {full_number}. Verifying...")
        self.update_ui("Confirmar?")
        pass

    def update_ui(self, status=None):
        if self.callback_fn:
            number_str = "".join(self.phone_number)
            self.callback_fn(number_str, status)

    def stop(self):
        self.running = False
