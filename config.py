import pyautogui
import json
import os

# --- CRITICAL PERFORMANCE SETTINGS ---
pyautogui.PAUSE = 0
pyautogui.FAILSAFE = False

# --- CONSTANTS ---
SETTINGS_FILE = "settings.json"

# --- DEFAULT USER SETTINGS ---
AUTO_START = True       
HEADLESS_DEFAULT = True 
AUDIO_START = False     # <--- NEW: Default to False if missing
RESOLUTION_ID = 0  
MODEL_COMPLEXITY = 0 
SENSITIVITY = 90
SMOOTHING = 4.0
CLICK_DIST = 27
RELEASE_DIST = 40
DEPTH_SCALE = 0.8
CAMERA_FPS = 30  # Default to 30

# --- SYSTEM STATE ---
running = False         
video_visible = False
headless_mode = True    

# --- MOUSE STATE ---
wScr, hScr = pyautogui.size()
plocX, plocY = 0, 0
dragging = False

# --- GESTURE FLAGS ---
right_clicked = False
pinky_triggered = False
keyboard_open = False
voice_enabled = False       
voice_active_gesture = False 
voice_status = "IDLE"

# --- PERSISTENCE LOGIC ---
def save_settings():
    data = {
        "SENSITIVITY": SENSITIVITY,
        "SMOOTHING": SMOOTHING,
        "CLICK_DIST": CLICK_DIST,
        "RELEASE_DIST": RELEASE_DIST,
        "DEPTH_SCALE": DEPTH_SCALE,
        "RESOLUTION_ID": RESOLUTION_ID,
        "MODEL_COMPLEXITY": MODEL_COMPLEXITY,
        "HEADLESS_DEFAULT": HEADLESS_DEFAULT,
        "AUTO_START": AUTO_START,
        "AUDIO_START": AUDIO_START, # <--- NEW: Save the preference
        "voice_enabled": voice_enabled ,
        "CAMERA_FPS": CAMERA_FPS
    }
    try:
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(data, f, indent=4)
        print("Configuration saved.")
    except Exception as e:
        print(f"Failed to save settings: {e}")

def load_settings():
    global SENSITIVITY, SMOOTHING, CLICK_DIST, RELEASE_DIST, DEPTH_SCALE
    global RESOLUTION_ID, MODEL_COMPLEXITY, HEADLESS_DEFAULT, AUTO_START, AUDIO_START
    global headless_mode, voice_enabled 
    global CAMERA_FPS
    
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r') as f:
                data = json.load(f)
                
            SENSITIVITY = data.get("SENSITIVITY", SENSITIVITY)
            SMOOTHING = data.get("SMOOTHING", SMOOTHING)
            CLICK_DIST = data.get("CLICK_DIST", CLICK_DIST)
            RELEASE_DIST = data.get("RELEASE_DIST", RELEASE_DIST)
            DEPTH_SCALE = data.get("DEPTH_SCALE", DEPTH_SCALE)
            RESOLUTION_ID = data.get("RESOLUTION_ID", RESOLUTION_ID)
            MODEL_COMPLEXITY = data.get("MODEL_COMPLEXITY", MODEL_COMPLEXITY)
            HEADLESS_DEFAULT = data.get("HEADLESS_DEFAULT", HEADLESS_DEFAULT)
            AUTO_START = data.get("AUTO_START", AUTO_START)
            AUDIO_START = data.get("AUDIO_START", AUDIO_START) # <--- NEW: Load preference
            CAMERA_FPS = data.get("CAMERA_FPS", 30)
            
            # Use AUDIO_START to determine initial voice state
            # If AUDIO_START is True, we force voice_enabled to True
            if AUDIO_START:
                voice_enabled = True
            else:
                voice_enabled = data.get("voice_enabled", False)
            
            headless_mode = HEADLESS_DEFAULT
            print("Configuration loaded.")
        except Exception as e:
            print(f"Failed to load settings: {e}")

load_settings()