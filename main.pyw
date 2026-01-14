import threading
import time
import cv2
import pystray
from PIL import Image, ImageDraw
import sys
import os

# Import our modules
import config
import camera
import tracking
import gui
import voice

def start_service():
    if not config.running:
        print("Requesting Start...")
        config.running = True

def stop_service():
    if config.running:
        print("Requesting Stop...")
        config.running = False

def main_loop():
    """Background thread that manages Hardware AND AI"""
    last_hand_time = time.time()
    
    while True:
        if config.running:
            # --- STARTUP LOGIC ---
            if not camera.is_camera_active():
                print("Initializing Hardware & AI...")
                # camera.init_camera now includes the 30 FPS hardware cap logic
                camera.init_camera(config.RESOLUTION_ID)
                tracking.init_hand_tracking(config.MODEL_COMPLEXITY)
                continue

            # --- NORMAL RUNNING LOGIC ---
            success, frame = camera.read_frame()
            if success:
                # 1. Process Frame (AI)
                # Note: tracking.process_frame should now update config.hand_detected
                processed_frame = tracking.process_frame(frame)
                
                # 2. Power Saving / Idle Logic
                if getattr(config, 'hand_detected', False):
                    last_hand_time = time.time()
                    idle_mode = False
                else:
                    # If no hand seen for > 2 seconds, enter low power mode
                    idle_mode = (time.time() - last_hand_time) > 2.0

                if idle_mode:
                    # Drop to ~10 FPS to save CPU while searching for a hand
                    time.sleep(0.1) 
                
                # 3. Display Logic
                # If headless, processed_frame will be None to save drawing cycles
                if not config.headless_mode and processed_frame is not None:
                    cv2.imshow("AI Mouse Camera", processed_frame)
                    config.video_visible = True
                    cv2.waitKey(1)
                
                elif config.headless_mode and config.video_visible:
                    try:
                        cv2.destroyWindow("AI Mouse Camera")
                        cv2.waitKey(1)
                    except Exception as e:
                        print(f"Window Close Error: {e}")
                    config.video_visible = False
            
        else:
            # --- STOPPED/CLEANUP LOGIC ---
            if camera.is_camera_active():
                print("Shutting down Hardware...")
                camera.release_camera()
                cv2.destroyAllWindows()
                config.video_visible = False
            
            time.sleep(0.5) # Deep sleep when not running

def toggle_headless(is_headless):
    config.headless_mode = bool(is_headless)
    config.HEADLESS_DEFAULT = config.headless_mode
   

# --- System Tray Logic ---
def create_tray_icon_image():
    width, height = 64, 64
    image = Image.new('RGB', (width, height), (255, 255, 255))
    dc = ImageDraw.Draw(image)
    dc.rectangle((0, 0, width, height), fill=(50, 50, 50))
    dc.ellipse((10, 10, 54, 54), fill=(0, 120, 215))
    dc.ellipse((28, 28, 36, 36), fill=(255, 255, 255))
    return image

def restore_window(icon, item):
    gui.root.after(0, gui.root.deiconify)

def quit_app(icon=None, item=None):
    try:
        gui.commit_settings_to_config()
    except Exception as e:
        print(f"Warning: Could not sync GUI settings: {e}")

    config.save_settings()
    
    if icon: 
        icon.stop()
    
    os._exit(0)

def run_tray_icon():
    image = create_tray_icon_image()
    menu = pystray.Menu(
        pystray.MenuItem("Settings", restore_window),
        pystray.MenuItem("Exit", quit_app)
    )
    icon = pystray.Icon("AIMouse", image, "AI Mouse Pro", menu)
    icon.run()

# --- Entry Point ---
if __name__ == "__main__":
    t_ai = threading.Thread(target=main_loop, daemon=True)
    t_ai.start()

    t_tray = threading.Thread(target=run_tray_icon, daemon=True)
    t_tray.start()

    voice.start_voice_thread()
    
    app = gui.create_window(start_service, stop_service, toggle_headless)
    
    if getattr(config, 'HEADLESS_DEFAULT', True):
        app.withdraw()
    
    if getattr(config, 'AUTO_START', True):
        start_service()

    app.mainloop()