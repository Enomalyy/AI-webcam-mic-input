# camera.py
import cv2

cap = None

def init_camera(res_id=0):
    global cap
    # Prevent double-initialization
    if cap is not None:
        return

    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FPS, 60)
    
    if res_id == 0:
        cap.set(3, 640)
        cap.set(4, 480)
    else:
        cap.set(3, 10000)
        cap.set(4, 10000)
    return cap

def read_frame():
    if cap and cap.isOpened():
        return cap.read()
    return False, None

def release_camera():
    global cap
    if cap:
        cap.release()
        cap = None

# --- NEW HELPER ---
def is_camera_active():
    return cap is not None