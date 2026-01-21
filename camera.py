import cv2
import config

# --- GLOBALS ---
cap = None

# Define available resolutions (Must match GUI IDs)
RESOLUTIONS = {
    0: (640, 480),   # Low Res (Fastest)
    1: (1280, 720)   # High Res (Better Tracking)
}

def init_camera(res_id=0):
    global cap
    if cap is not None:
        cap.release()
    
    # Force DirectShow (Standard for Windows)
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    
    # --- 1. MJPG COMPRESSION ---
    if config.USE_MJPG:
        try:
            fourcc = cv2.VideoWriter_fourcc(*'MJPG')
            cap.set(cv2.CAP_PROP_FOURCC, fourcc)
            print("[Camera] MJPG Compression ENABLED")
        except:
            print("[Camera] Warning: MJPG not supported.")
    else:
        print("[Camera] MJPG Compression DISABLED (Standard)")

    # --- 2. RESOLUTION & FPS ---
    width, height = RESOLUTIONS.get(res_id, (640, 480))
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    
    cap.set(cv2.CAP_PROP_FPS, config.CAMERA_FPS)
    print(f"[Camera] Requested FPS: {config.CAMERA_FPS}")

    # --- 3. EXPOSURE (Default to Auto) ---
    # We now rely on the user opening the Settings Panel to fix Low Light Comp
    cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.75) # Auto

    if not cap.isOpened():
        print("Error: Could not open camera.")

def open_settings_panel():
    """Opens the Windows Native Camera Settings Dialog"""
    global cap
    if cap and cap.isOpened():
        # This magic command forces the driver window to appear
        cap.set(cv2.CAP_PROP_SETTINGS, 1)

def read_frame():
    global cap
    if cap is None or not cap.isOpened():
        return False, None
    success, img = cap.read()
    return success, img

def is_camera_active():
    global cap
    return cap is not None and cap.isOpened()

def release_camera():
    global cap
    if cap is not None:
        cap.release()
        cap = None