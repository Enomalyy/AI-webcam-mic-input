import tkinter as tk
import config
import pyautogui
import camera  # Essential import

# Define globals
root = None
scale_sens = None
scale_smooth = None
scale_click = None
scale_release = None
scale_depth = None
var_head = None
var_res = None
var_model = None
var_voice = None
var_audio_start = None

class StatusOverlay:
    def __init__(self, master):
        self.top = tk.Toplevel(master)
        self.top.title("AI Status")
        self.top.overrideredirect(True)
        self.top.wm_attributes("-topmost", True)
        self.top.wm_attributes("-disabled", True)
        self.bg_color = "#ffffff"
        self.top.config(bg=self.bg_color)
        self.top.wm_attributes("-transparentcolor", self.bg_color)
        self.width = 60
        self.height = 60
        self.top.geometry(f"{self.width}x{self.height}+0+0")
        self.canvas = tk.Canvas(self.top, width=self.width, height=self.height, bg=self.bg_color, highlightthickness=0)
        self.canvas.pack()
        self.circle = self.canvas.create_oval(5, 5, 55, 55, fill="gray", outline="")
        self.text = self.canvas.create_text(30, 30, text="", fill="white", font=("Arial", 10, "bold"))
        self.update_overlay()

    def update_overlay(self):
        if not config.voice_enabled:
            self.top.withdraw()
        else:
            try:
                x, y = int(config.plocX), int(config.plocY)
                self.top.geometry(f"+{x + 30}+{y + 30}")
            except: pass

            color = self.bg_color
            text_str = ""
            
            if config.voice_active_gesture:
                if config.voice_status == "IDLE":
                    color = "#ffd700" 
                    text_str = "MIC"
                elif config.voice_status == "LISTENING":
                    color = "#ff4444" 
                    text_str = "REC"
            
            if config.voice_status == "PROCESSING":
                color = "#4444ff" 
                text_str = "..."

            if color == self.bg_color:
                self.top.withdraw()
            else:
                self.top.deiconify()
                self.canvas.itemconfig(self.circle, fill=color)
                self.canvas.itemconfig(self.text, text=text_str)

        self.top.after(40, self.update_overlay)

def commit_settings_to_config():
    """Reads all GUI variables and pushes them to config.py"""
    try:
        if scale_sens: config.SENSITIVITY = int(scale_sens.get())
        if scale_smooth: config.SMOOTHING = float(scale_smooth.get())
        if scale_click: config.CLICK_DIST = int(scale_click.get())
        if scale_release: config.RELEASE_DIST = int(scale_release.get())
        if scale_depth: config.DEPTH_SCALE = float(scale_depth.get())
        if var_res: config.RESOLUTION_ID = var_res.get()
        if var_model: config.MODEL_COMPLEXITY = var_model.get()
        if var_head: config.HEADLESS_DEFAULT = bool(var_head.get())
        if var_voice: config.voice_enabled = bool(var_voice.get())
        if var_audio_start: config.AUDIO_START = bool(var_audio_start.get())
        print("GUI Settings synced to Config.")
    except Exception as e:
        print(f"Error syncing settings: {e}")

def update_config_from_ui(val=None):
    # Live update (for responsiveness)
    if scale_sens: config.SENSITIVITY = int(scale_sens.get())
    if scale_smooth: config.SMOOTHING = float(scale_smooth.get())
    if scale_click: config.CLICK_DIST = int(scale_click.get())
    if scale_release: config.RELEASE_DIST = int(scale_release.get())
    if scale_depth: config.DEPTH_SCALE = float(scale_depth.get())

def create_window(start_callback, stop_callback, headless_callback):
    global root, scale_sens, scale_smooth, scale_click, scale_release, scale_depth
    global var_head, var_res, var_model, var_voice, var_audio_start
    
    root = tk.Tk()
    root.title("AI Mouse")
    root.geometry("320x760") # Increased height slightly for new slider
    
    default_head = getattr(config, 'HEADLESS_DEFAULT', True)
    default_res = getattr(config, 'RESOLUTION_ID', 0)
    default_voice = getattr(config, 'voice_enabled', False)
    default_audio_start = getattr(config, 'AUDIO_START', False)
    
    var_head = tk.IntVar(value=1 if default_head else 0)
    var_res = tk.IntVar(value=default_res)
    var_model = tk.IntVar(value=0)
    var_voice = tk.IntVar(value=1 if default_voice else 0)
    var_audio_start = tk.IntVar(value=1 if default_audio_start else 0)

    # --- RESOLUTION LOGIC FIX ---
    def on_res_change():
        config.RESOLUTION_ID = var_res.get()
        print(f"Resolution set to ID: {config.RESOLUTION_ID}")

    frame_top = tk.Frame(root)
    frame_top.pack(pady=10)
    
    # Updated command to use specific resolution handler
    tk.Radiobutton(frame_top, text="Low Res", variable=var_res, value=0, command=on_res_change).pack(side="left")
    tk.Radiobutton(frame_top, text="High Res", variable=var_res, value=1, command=on_res_change).pack(side="left")
    # ----------------------------

    tk.Checkbutton(root, text="Headless (No Video)", variable=var_head, command=lambda: headless_callback(var_head.get())).pack()
    
    voice_frame = tk.Frame(root, bd=1, relief="sunken", padx=5, pady=5)
    voice_frame.pack(pady=5, fill="x", padx=20)
    
    tk.Checkbutton(voice_frame, text="Enable Voice Typing", variable=var_voice, command=lambda: setattr(config, 'voice_enabled', bool(var_voice.get()))).pack(anchor="w")
    tk.Checkbutton(voice_frame, text="Auto-Start Voice at Launch", variable=var_audio_start).pack(anchor="w", padx=20) 

    btn_frame = tk.Frame(root)
    btn_frame.pack(pady=10)
    tk.Button(btn_frame, text="START", bg="#ccffcc", command=start_callback, width=10).pack(side="left", padx=5)
    tk.Button(btn_frame, text="STOP", bg="#ffcccc", command=stop_callback, width=10).pack(side="left", padx=5)

    tk.Label(root, text="Sensitivity").pack()
    scale_sens = tk.Scale(root, from_=50, to=400, orient="horizontal", command=update_config_from_ui)
    scale_sens.set(config.SENSITIVITY)
    scale_sens.pack(fill="x", padx=20)

    tk.Label(root, text="Smoothing").pack()
    scale_smooth = tk.Scale(root, from_=1, to=15, orient="horizontal", command=update_config_from_ui)
    scale_smooth.set(config.SMOOTHING)
    scale_smooth.pack(fill="x", padx=20)

    tk.Label(root, text="Click Distance").pack()
    scale_click = tk.Scale(root, from_=10, to=100, orient="horizontal", command=update_config_from_ui)
    scale_click.set(config.CLICK_DIST)
    scale_click.pack(fill="x", padx=20)

    tk.Label(root, text="Release Distance").pack()
    scale_release = tk.Scale(root, from_=20, to=120, orient="horizontal", command=update_config_from_ui)
    scale_release.set(config.RELEASE_DIST)
    scale_release.pack(fill="x", padx=20)

    tk.Label(root, text="Hand Depth Scale").pack()
    scale_depth = tk.Scale(root, from_=0.0, to=2.0, resolution=0.1, orient="horizontal", command=update_config_from_ui)
    scale_depth.set(config.DEPTH_SCALE)
    scale_depth.pack(fill="x", padx=20)

    # --- FPS SLIDER SECTION ---
    lbl_fps = tk.Label(root, text=f"Camera FPS: {config.CAMERA_FPS}", font=("Segoe UI", 10))
    lbl_fps.pack(pady=(10, 0))

    def on_fps_change(val):
        fps_val = int(val)
        lbl_fps.config(text=f"Camera FPS: {fps_val}")
        # Safe update only
        config.CAMERA_FPS = fps_val

    scale_fps = tk.Scale(root, from_=10, to=60, orient=tk.HORIZONTAL, length=280, command=on_fps_change)
    scale_fps.set(config.CAMERA_FPS) 
    scale_fps.pack(pady=5)
    # --------------------------

    root.after(500, lambda: StatusOverlay(root))

    root.protocol("WM_DELETE_WINDOW", root.withdraw)
    root.bind('<<Restore>>', lambda e: root.deiconify())
    
    return root