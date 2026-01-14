import cv2
import time
import config

cap = None

def init_camera(res_id):
    global cap
    # Using CAP_DSHOW is faster on Windows, but sometimes unstable. 
    # If crashes persist, try removing '+ cv2.CAP_DSHOW'
    cap = cv2.VideoCapture(0 + cv2.CAP_DSHOW)
    
    cap.set(cv2.CAP_PROP_FPS, config.CAMERA_FPS)
    
    width = 10000 if res_id == 1 else 640
    height = 10000 if res_id == 1 else 480
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

def read_frame():
    global cap
    if cap is None or not cap.isOpened():
        return False, None
    
    try:
        success, frame = cap.read()
        if not success:
            return False, None
        return True, frame
        
    except cv2.error as e:
        print(f"OpenCV Error (Ignored): {e}")
        # Return failure so the main loop can decide to re-init or wait
        return False, None
    except Exception as e:
        print(f"Camera General Error: {e}")
        return False, None

def is_camera_active():
    return cap is not None and cap.isOpened()

def release_camera():
    global cap
    if cap is not None:
        cap.release()
        cap = None