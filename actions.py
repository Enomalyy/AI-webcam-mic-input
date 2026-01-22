import pyautogui
import touch_engine
import config
import keyboard
import ctypes
from ctypes import c_long, c_ulong, Structure, Union, POINTER, sizeof, byref

# --- LOW-LEVEL INPUT (Hardware Jiggle) ---
class MOUSEINPUT(Structure):
    _fields_ = [("dx", c_long), ("dy", c_long), ("mouseData", c_ulong), ("dwFlags", c_ulong), ("time", c_ulong), ("dwExtraInfo", POINTER(c_ulong))]
class INPUT_I(Union):
    _fields_ = [("mi", MOUSEINPUT)]
class INPUT(Structure):
    _fields_ = [("type", c_ulong), ("ii", INPUT_I)]
MOUSEEVENTF_MOVE = 0x0001
INPUT_MOUSE = 0

# --- STATE ---
is_index_down = False
is_middle_down = False 
is_mouse_down = False 

# --- TRANSITION GUARD ---
# Prevents the "Right Click" glitch by delaying the 'Down' signal 
# during mode switches so fingers can stabilize.
mode_transition_frames = 0
MODE_GUARD_THRESHOLD = 3 

# --- DRAG STABILITY ---
drag_start_x = 0
drag_start_y = 0
is_drag_locked = False
DRAG_THRESHOLD = 25
DRAG_THRESHOLD_SQ = DRAG_THRESHOLD ** 2

# --- GESTURES ---
pinky_frames = 0
GESTURE_THRESHOLD = 5

def inject_hardware_jiggle():
    """Forces Windows to show the mouse cursor again."""
    try:
        mi = MOUSEINPUT(1, 0, 0, MOUSEEVENTF_MOVE, 0, None)
        inp = INPUT(INPUT_MOUSE, INPUT_I(mi=mi))
        ctypes.windll.user32.SendInput(1, byref(inp), sizeof(INPUT))
    except: pass

def handle_input(index_x, index_y, mid_x, mid_y, is_pinched, is_two_finger_mode):
    global is_index_down, is_middle_down, is_mouse_down
    global drag_start_x, drag_start_y, is_drag_locked, mode_transition_frames

    if index_x <= 1 and index_y <= 1:
        return

    touch_attempted = False
    touch_success = False

    # ==========================================
    # 1. DUAL TOUCH MODE (Scrolling / Zooming)
    # ==========================================
    if is_two_finger_mode and touch_engine.TOUCH_AVAILABLE:
        touch_attempted = True
        is_drag_locked = False 
        
        # ID 0: Index
        touch_engine.update_touch(0, index_x, index_y, is_down=True)
        is_index_down = True
        
        # ID 1: Middle
        if mid_x > 0 and mid_y > 0:
            touch_engine.update_touch(1, mid_x, mid_y, is_down=True)
            is_middle_down = True
            
        if is_mouse_down:
            pyautogui.mouseUp()
            is_mouse_down = False

    # ==========================================
    # 2. SINGLE TOUCH MODE (Clicking / Dragging)
    # ==========================================
    elif touch_engine.TOUCH_AVAILABLE:
        touch_attempted = True
        
        # Clean up Middle Finger if it was just released
        if is_middle_down:
            touch_engine.update_touch(1, mid_x, mid_y, is_down=False)
            is_middle_down = False

        if is_pinched:
            if not is_index_down:
                # START NEW PINCH
                is_index_down = True
                is_drag_locked = True
                drag_start_x, drag_start_y = index_x, index_y
                
                touch_engine.update_touch(0, drag_start_x, drag_start_y, is_down=True)
                
                if is_mouse_down:
                    pyautogui.mouseUp()
                    is_mouse_down = False
            else:
                # CONTINUING DRAG
                target_x, target_y = index_x, index_y
                if is_drag_locked:
                    if (index_x - drag_start_x)**2 + (index_y - drag_start_y)**2 < DRAG_THRESHOLD_SQ:
                        target_x, target_y = drag_start_x, drag_start_y
                    else:
                        is_drag_locked = False
                
                touch_engine.update_touch(0, target_x, target_y, is_down=True)
        else:
            # RELEASE / HOVER
            if is_index_down:
                touch_engine.update_touch(0, index_x, index_y, is_down=False)
                is_index_down = False
                is_drag_locked = False
                inject_hardware_jiggle() 
            else:
                # Visual Mouse Update (Hover)
                try:
                    ctypes.windll.user32.SetCursorPos(int(index_x), int(index_y))
                except: pass

    # ==========================================
    # 3. COMMIT FRAME & FALLBACK
    # ==========================================
    if touch_attempted:
        touch_success = touch_engine.process_frame()

    # Fallback to standard mouse if touch fails
    if not touch_success and not is_two_finger_mode:
        if is_pinched and not is_mouse_down:
            pyautogui.mouseDown()
            is_mouse_down = True
        elif not is_pinched and is_mouse_down:
            pyautogui.mouseUp()
            is_mouse_down = False

    handle_gestures(getattr(config, 'pinky_bent', False))

def handle_gestures(is_pinky_down):
    global pinky_frames
    if is_pinky_down:
        pinky_frames += 1
    else:
        pinky_frames = 0
    
    if pinky_frames > GESTURE_THRESHOLD and not getattr(config, 'keyboard_triggered', False):
        keyboard.toggle()
        config.keyboard_triggered = True
    elif pinky_frames == 0:
        config.keyboard_triggered = False

def release_all():
    """Safety cleanup called when hand is lost."""
    global is_index_down, is_middle_down, is_mouse_down
    
    if touch_engine.TOUCH_AVAILABLE:
        needs_update = False
        if is_index_down:
            touch_engine.update_touch(0, 0, 0, is_down=False)
            is_index_down = False
            needs_update = True
        if is_middle_down:
            touch_engine.update_touch(1, 0, 0, is_down=False)
            is_middle_down = False
            needs_update = True
            
        if needs_update:
            touch_engine.process_frame()
            inject_hardware_jiggle()
        
    if is_mouse_down:
        pyautogui.mouseUp()
        is_mouse_down = False