import threading
import queue
import time
import numpy as np
import sounddevice as sd
import webrtcvad
import pyautogui
import config
import gc
from faster_whisper import WhisperModel

# --- AUDIO CONFIGURATION ---
SAMPLE_RATE = 16000
FRAME_DURATION_MS = 20
FRAME_SIZE = int(SAMPLE_RATE * FRAME_DURATION_MS / 1000) # 320 samples
SILENCE_TIMEOUT_MS = 900
SILENCE_CHUNKS = int(SILENCE_TIMEOUT_MS / FRAME_DURATION_MS)

# --- AI CONFIGURATION ---
MODEL_SIZE = "tiny.en"
COMPUTE_TYPE = "int8"

# --- GLOBALS ---
model = None
audio_queue = queue.Queue(maxsize=500) # Limit buffer to ~10 seconds of audio
vad = webrtcvad.Vad(2) # Mode 2 = Balanced (Aggressive enough to filter breathing)

def load_model():
    global model
    if model is None:
        try:
            print("[Voice] Loading Whisper Model...")
            config.voice_status = "LOADING"
            # Threads=1 prevents UI lag during heavy CPU math
            model = WhisperModel(MODEL_SIZE, device="cpu", compute_type=COMPUTE_TYPE, cpu_threads=2)
            print("[Voice] Model Ready.")
            return True
        except Exception as e:
            print(f"[Voice] Load Error: {e}")
            return False
    return True

def unload_model():
    global model
    if model is not None:
        del model
        model = None
        gc.collect()
        config.voice_status = "IDLE"

def audio_callback(indata, frames, time, status):
    """
    Real-time audio callback. 
    Must be lightning fast. Just puts data in the queue.
    """
    if status:
        print(f"[Audio] Error: {status}")
    # Copy data to queue
    audio_queue.put(bytes(indata))

def transcribe_buffer(buffer_bytes):
    """Run Whisper on the collected bytes"""
    global model
    
    if not buffer_bytes or model is None: 
        return

    config.voice_status = "PROCESSING"
    print(f"[Voice] Processing {len(buffer_bytes)/32000:.1f}s of audio...")

    try:
        # 1. Convert raw PCM bytes to Float32 array for Whisper
        # Webrtcvad uses 16-bit int, Whisper uses 32-bit float [-1, 1]
        audio_int16 = np.frombuffer(buffer_bytes, dtype=np.int16)
        audio_float32 = audio_int16.astype(np.float32) / 32768.0

        # 2. Transcribe
        segments, info = model.transcribe(audio_float32, beam_size=5)
        
        text = " ".join([seg.text for seg in segments]).strip()
        
        # --- SMART PUNCTUATION LOGIC ---
        # If text is short (command-like) and ends with a period, remove it.
        if len(text) < 25 and text.endswith("."):
            text = text[:-1]
        # -------------------------------
        
        if text:
            print(f"[Voice] TYPING: {text}")
            pyautogui.write(text + " ")
        else:
            print("[Voice] (Silence/Noise ignored)")

    except Exception as e:
        print(f"[Voice] Transcribe Error: {e}")
    
    config.voice_status = "IDLE"

def processing_loop():
    """Main logic thread: VAD State Machine"""
    
    # State variables
    triggered = False
    silence_counter = 0
    buffer = bytearray()
    
    while True:
        # A. Master Switch Check
        if not config.voice_enabled:
            if model is not None: unload_model()
            time.sleep(0.5)
            continue
        
        # B. Load Model if needed
        if model is None:
            if not load_model():
                time.sleep(5)
                continue

        # C. Start Microphone Stream
        # We open the stream and keep it open as long as voice is enabled
        try:
            with sd.RawInputStream(samplerate=SAMPLE_RATE, 
                                   blocksize=FRAME_SIZE, 
                                   dtype='int16', 
                                   channels=1, 
                                   callback=audio_callback):
                
                print("[Voice] Stream Started. Waiting for gesture...")
                
                while config.voice_enabled:
                    # 1. Get audio frame (blocking wait)
                    try:
                        frame = audio_queue.get(timeout=1.0)
                    except queue.Empty:
                        continue
                    
                    # 2. GESTURE CHECK (The Gating Layer)
                    # If user is NOT holding the gesture, we reset everything.
                    if not config.voice_active_gesture:
                        if triggered:
                            # If we WERE recording and user let go, maybe we process?
                            # For safety/cleanliness, we dump it. 
                            # If you want "Release-to-Send", change this block.
                            buffer.clear()
                            triggered = False
                            config.voice_status = "IDLE"
                        continue

                    # 3. VAD Check
                    is_speech = vad.is_speech(frame, SAMPLE_RATE)

                    if not triggered:
                        if is_speech:
                            print("[Voice] Speech Detected -> Recording")
                            triggered = True
                            config.voice_status = "LISTENING"
                            buffer.extend(frame)
                            silence_counter = 0
                    else:
                        # We are currently recording an utterance
                        buffer.extend(frame)
                        
                        if is_speech:
                            silence_counter = 0
                        else:
                            silence_counter += 1

                        # 4. End of Utterance Check
                        if silence_counter > SILENCE_CHUNKS:
                            # 900ms of silence detected. Finish.
                            transcribe_buffer(bytes(buffer))
                            
                            # Reset
                            buffer.clear()
                            triggered = False
                            silence_counter = 0

        except Exception as e:
            print(f"[Voice] Stream Error: {e}")
            time.sleep(1)

def start_voice_thread():
    t = threading.Thread(target=processing_loop, daemon=True)
    t.start()