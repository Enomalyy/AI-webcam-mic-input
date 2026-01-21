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
AUDIO_START = False     
RESOLUTION_ID = 0  
MODEL_COMPLEXITY = 0 
SENSITIVITY = 90
SMOOTHING = 4.0
CLICK_DIST = 27
RELEASE_DIST = 40
DEPTH_SCALE = 0.8
CAMERA_FPS = 30  
USE_MJPG = False 
AUTO_EXPOSURE = True   
EXPOSURE_VAL = -3
GAIN_VAL = 64
BOX_OFFSET_X = 0   # Horizontal Shift
BOX_OFFSET_Y = 0   # Vertical Shift

# --- SYSTEM STATE ---
running = False         
video_visible = False
headless_mode = True    
hand_detected = False

# --- MOUSE STATE ---
wScr, hScr = pyautogui.size()
plocX, plocY = 0, 0
clocX, clocY = 0, 0
dragging = False

# --- GESTURE FLAGS ---
right_clicked = False
pinky_triggered = False
keyboard_open = False
voice_enabled = False       
voice_active_gesture = False 
voice_status = "IDLE"
VOICE_ALWAYS_ON = False

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
        "AUDIO_START": AUDIO_START, 
        "voice_enabled": voice_enabled,
        "CAMERA_FPS": CAMERA_FPS,
        # --- NEW PERSISTENT SETTINGS ---
        "USE_MJPG": USE_MJPG,
        "AUTO_EXPOSURE": AUTO_EXPOSURE,
        "EXPOSURE_VAL": EXPOSURE_VAL,
        "BOX_OFFSET_X": BOX_OFFSET_X,
        "BOX_OFFSET_Y": BOX_OFFSET_Y,
        "VOICE_ALWAYS_ON": VOICE_ALWAYS_ON
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
    # Import the new globals so we can write to them
    global USE_MJPG, AUTO_EXPOSURE, EXPOSURE_VAL, BOX_OFFSET_X, BOX_OFFSET_Y
    global BOX_OFFSET_X, BOX_OFFSET_Y
    global VOICE_ALWAYS_ON
    
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
            AUDIO_START = data.get("AUDIO_START", AUDIO_START)
            CAMERA_FPS = data.get("CAMERA_FPS", CAMERA_FPS)
            
            # --- LOAD NEW SETTINGS ---
            USE_MJPG = data.get("USE_MJPG", USE_MJPG)
            AUTO_EXPOSURE = data.get("AUTO_EXPOSURE", AUTO_EXPOSURE)
            EXPOSURE_VAL = data.get("EXPOSURE_VAL", EXPOSURE_VAL)
            BOX_OFFSET_X = data.get("BOX_OFFSET_X", BOX_OFFSET_X)
            BOX_OFFSET_Y = data.get("BOX_OFFSET_Y", BOX_OFFSET_Y)
            
            if AUDIO_START:
                voice_enabled = True
            else:
                voice_enabled = data.get("voice_enabled", False)
            
            headless_mode = HEADLESS_DEFAULT
            print("Configuration loaded.")
        except Exception as e:
            print(f"Failed to load settings: {e}")

load_settings()