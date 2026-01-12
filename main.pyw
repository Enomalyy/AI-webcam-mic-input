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
    while True:
        if config.running:
            # --- STARTUP LOGIC ---
            # If the flag is ON but camera is OFF, we need to initialize everything.
            if not camera.is_camera_active():
                print("Initializing Hardware & AI...")
                # 1. Open Camera
                camera.init_camera(config.RESOLUTION_ID)
                
                # 2. LOAD AI MODEL (This was missing!)
                tracking.init_hand_tracking(config.MODEL_COMPLEXITY)
                
                # Skip this frame to allow sensors to warm up
                continue

            # --- NORMAL RUNNING LOGIC ---
            success, frame = camera.read_frame()
            if success:
                processed_frame = tracking.process_frame(frame)
                
                # Display Logic
                if not config.headless_mode and processed_frame is not None:
                    cv2.imshow("AI Mouse Camera", processed_frame)
                    config.video_visible = True
                    cv2.waitKey(1)
                
                elif config.headless_mode and config.video_visible:
                    cv2.destroyAllWindows()
                    config.video_visible = False
            
        else:
            # --- STOPPED/CLEANUP LOGIC ---
            if camera.is_camera_active():
                print("Shutting down Hardware...")
                camera.release_camera()
                # We don't explicitly destroy 'hands' here because MediaPipe 
                # handles its own garbage collection fairly well, but we could if needed.
                cv2.destroyAllWindows()
                config.video_visible = False
            
            time.sleep(0.1)

def toggle_headless(is_headless):
    config.headless_mode = bool(is_headless)
    # Update the preference so it can be saved
    config.HEADLESS_DEFAULT = config.headless_mode
    
    if config.headless_mode:
        cv2.destroyAllWindows()
        config.video_visible = False

# --- System Tray Logic ---
def create_tray_icon_image():
    width = 64
    height = 64
    image = Image.new('RGB', (width, height), (255, 255, 255))
    dc = ImageDraw.Draw(image)
    dc.rectangle((0, 0, width, height), fill=(50, 50, 50))
    dc.ellipse((10, 10, 54, 54), fill=(0, 120, 215))
    dc.ellipse((28, 28, 36, 36), fill=(255, 255, 255))
    return image

def restore_window(icon, item):
    gui.root.after(0, gui.root.deiconify)

def quit_app(icon=None, item=None):
    # 1. FORCE SYNC: Grab values from GUI sliders/checkboxes
    # This assumes 'gui' module is imported and the window exists
    try:
        gui.commit_settings_to_config()
    except Exception as e:
        print(f"Warning: Could not sync GUI settings: {e}")

    # 2. Save Settings to Disk
    config.save_settings()
    
    # 3. Stop the Icon loop
    if icon: 
        icon.stop()
    
    # 4. Force Kill
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