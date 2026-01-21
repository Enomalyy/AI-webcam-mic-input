import tkinter as tk
import config
import camera

# Define globals
root = None
scale_sens = None
scale_smooth = None
scale_click = None
scale_release = None
scale_depth = None
scale_fps = None
scale_off_x = None
scale_off_y = None

var_head = None
var_res = None
var_model = None
var_voice = None
var_voice_always = None # <--- NEW
var_audio_start = None
var_mjpg = None

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
            # 1. Position Logic
            # If camera is running, follow the mouse/hand
            try:
                if config.running and config.hand_detected:
                     x, y = int(config.plocX), int(config.plocY)
                     self.top.geometry(f"+{x + 30}+{y + 30}")
                elif config.VOICE_ALWAYS_ON:
                     # If camera is OFF but Voice is Always On,
                     # Park the overlay in the bottom-right corner (or top-right)
                     # so the user knows the mic is live.
                     scr_w, scr_h = self.top.winfo_screenwidth(), self.top.winfo_screenheight()
                     self.top.geometry(f"+{scr_w - 80}+{scr_h - 150}")
            except: pass

            color = self.bg_color
            text_str = ""
            
            # 2. Color Logic
            if config.voice_status == "PROCESSING":
                color = "#4444ff" # Blue (Processing)
                text_str = "..."
            elif config.VOICE_ALWAYS_ON:
                color = "#00ffff" # Cyan (Always On Mode)
                text_str = "ON"
            elif config.voice_active_gesture:
                if config.voice_status == "IDLE":
                    color = "#ffd700" # Gold (Gesture Detected, Ready)
                    text_str = "MIC"
                elif config.voice_status == "LISTENING":
                    color = "#ff4444" # Red (Recording)
                    text_str = "REC"
            
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
        if scale_off_x: config.BOX_OFFSET_X = int(scale_off_x.get())
        if scale_off_y: config.BOX_OFFSET_Y = int(scale_off_y.get())
        
        if var_res: config.RESOLUTION_ID = var_res.get()
        if var_model: config.MODEL_COMPLEXITY = var_model.get()
        if var_head: config.HEADLESS_DEFAULT = bool(var_head.get())
        if var_voice: config.voice_enabled = bool(var_voice.get())
        if var_voice_always: config.VOICE_ALWAYS_ON = bool(var_voice_always.get())
        if var_audio_start: config.AUDIO_START = bool(var_audio_start.get())
        if var_mjpg: config.USE_MJPG = bool(var_mjpg.get())
        if scale_fps: config.CAMERA_FPS = int(scale_fps.get())

        print("GUI Settings synced to Config.")
    except Exception as e:
        print(f"Error syncing settings: {e}")

def update_config_from_ui(val=None):
    if scale_sens: config.SENSITIVITY = int(scale_sens.get())
    if scale_smooth: config.SMOOTHING = float(scale_smooth.get())
    if scale_click: config.CLICK_DIST = int(scale_click.get())
    if scale_release: config.RELEASE_DIST = int(scale_release.get())
    if scale_depth: config.DEPTH_SCALE = float(scale_depth.get())
    if scale_off_x: config.BOX_OFFSET_X = int(scale_off_x.get())
    if scale_off_y: config.BOX_OFFSET_Y = int(scale_off_y.get())

def create_window(start_callback, stop_callback, headless_callback):
    global root, scale_sens, scale_smooth, scale_click, scale_release, scale_depth, scale_fps
    global scale_off_x, scale_off_y
    global var_head, var_res, var_model, var_voice, var_voice_always, var_audio_start, var_mjpg
    
    root = tk.Tk()
    root.title("AI Mouse")
    root.geometry("340x950") 
    
    default_head = getattr(config, 'HEADLESS_DEFAULT', True)
    default_res = getattr(config, 'RESOLUTION_ID', 0)
    default_voice = getattr(config, 'voice_enabled', False)
    default_voice_always = getattr(config, 'VOICE_ALWAYS_ON', False)
    default_audio_start = getattr(config, 'AUDIO_START', False)
    default_mjpg = getattr(config, 'USE_MJPG', True)
    default_off_x = getattr(config, 'BOX_OFFSET_X', 0)
    default_off_y = getattr(config, 'BOX_OFFSET_Y', 0)
    
    var_head = tk.IntVar(value=1 if default_head else 0)
    var_res = tk.IntVar(value=default_res)
    var_model = tk.IntVar(value=0)
    var_voice = tk.IntVar(value=1 if default_voice else 0)
    var_voice_always = tk.IntVar(value=1 if default_voice_always else 0)
    var_audio_start = tk.IntVar(value=1 if default_audio_start else 0)
    var_mjpg = tk.IntVar(value=1 if default_mjpg else 0)

    def on_res_change():
        config.RESOLUTION_ID = var_res.get()

    frame_top = tk.Frame(root)
    frame_top.pack(pady=10)
    tk.Radiobutton(frame_top, text="Low Res", variable=var_res, value=0, command=on_res_change).pack(side="left")
    tk.Radiobutton(frame_top, text="High Res", variable=var_res, value=1, command=on_res_change).pack(side="left")

    tk.Checkbutton(root, text="Headless (No Video)", variable=var_head, command=lambda: headless_callback(var_head.get())).pack()
    
    def on_mjpg_change():
        config.USE_MJPG = bool(var_mjpg.get())
    tk.Checkbutton(root, text="Force MJPG (Fix Lag)", variable=var_mjpg, command=on_mjpg_change).pack()
    
    # --- CAMERA HARDWARE SETTINGS ---
    cam_frame = tk.Frame(root, bd=1, relief="groove", padx=5, pady=5)
    cam_frame.pack(fill="x", padx=20, pady=5)
    tk.Label(cam_frame, text="Hardware Settings", font=("Segoe UI", 9, "bold")).pack()
    tk.Button(cam_frame, text="Open Driver Panel (Disable Low Light)", command=camera.open_settings_panel).pack(fill="x", pady=2)

    # --- BOX POSITION CONTROLS ---
    pos_frame = tk.Frame(root, bd=1, relief="sunken", padx=5, pady=5)
    pos_frame.pack(fill="x", padx=20, pady=10)
    tk.Label(pos_frame, text="Active Zone Position", font=("Segoe UI", 9, "bold")).pack()
    
    tk.Label(pos_frame, text="Move Left/Right").pack(anchor="w")
    scale_off_x = tk.Scale(pos_frame, from_=-200, to=200, orient="horizontal", command=update_config_from_ui)
    scale_off_x.set(default_off_x)
    scale_off_x.pack(fill="x")

    tk.Label(pos_frame, text="Move Up/Down").pack(anchor="w")
    scale_off_y = tk.Scale(pos_frame, from_=-200, to=200, orient="horizontal", command=update_config_from_ui)
    scale_off_y.set(default_off_y)
    scale_off_y.pack(fill="x")

    # --- VOICE CONTROLS (Updated) ---
    voice_frame = tk.Frame(root, bd=1, relief="sunken", padx=5, pady=5)
    voice_frame.pack(pady=5, fill="x", padx=20)
    tk.Label(voice_frame, text="Voice Control", font=("Segoe UI", 9, "bold")).pack()
    
    tk.Checkbutton(voice_frame, text="Enable Voice Engine", variable=var_voice, command=lambda: setattr(config, 'voice_enabled', bool(var_voice.get()))).pack(anchor="w")
    
    def on_always_voice():
        config.VOICE_ALWAYS_ON = bool(var_voice_always.get())
    tk.Checkbutton(voice_frame, text="Always-On Mode (No Gesture)", variable=var_voice_always, command=on_always_voice, fg="blue").pack(anchor="w", padx=10)
    
    tk.Checkbutton(voice_frame, text="Auto-Start Voice", variable=var_audio_start).pack(anchor="w", padx=10) 
    # --------------------------------

    btn_frame = tk.Frame(root)
    btn_frame.pack(pady=10)
    tk.Button(btn_frame, text="START", bg="#ccffcc", command=start_callback, width=10).pack(side="left", padx=5)
    tk.Button(btn_frame, text="STOP", bg="#ffcccc", command=stop_callback, width=10).pack(side="left", padx=5)

    tk.Label(root, text="Sensitivity (Box Size)").pack()
    scale_sens = tk.Scale(root, from_=20, to=400, orient="horizontal", command=update_config_from_ui)
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

    lbl_fps = tk.Label(root, text=f"Target FPS: {config.CAMERA_FPS}", font=("Segoe UI", 10))
    lbl_fps.pack(pady=(10, 0))
    def on_fps_change(val):
        fps_val = int(val)
        lbl_fps.config(text=f"Target FPS: {fps_val}")
        config.CAMERA_FPS = fps_val
    scale_fps = tk.Scale(root, from_=10, to=60, orient=tk.HORIZONTAL, length=280, command=on_fps_change)
    scale_fps.set(config.CAMERA_FPS) 
    scale_fps.pack(pady=5)

    root.after(500, lambda: StatusOverlay(root))
    root.protocol("WM_DELETE_WINDOW", root.withdraw)
    root.bind('<<Restore>>', lambda e: root.deiconify())
    
    return root