import ctypes
from ctypes import *
from ctypes.wintypes import *

# --- TYPES & CONSTANTS (Matching your working file) ---
POINTER_FLAG_NONE = 0x00000000
POINTER_FLAG_NEW = 0x00000001
POINTER_FLAG_INRANGE = 0x00000002
POINTER_FLAG_INCONTACT = 0x00000004
POINTER_FLAG_DOWN = 0x00010000
POINTER_FLAG_UPDATE = 0x00020000
POINTER_FLAG_UP = 0x00040000

TOUCH_MASK_NONE = 0x00000000
TOUCH_MASK_CONTACTAREA = 0x00000001
TOUCH_MASK_ORIENTATION = 0x00000002
TOUCH_MASK_PRESSURE = 0x00000004
TOUCH_MASK_ALL = 0x00000007

PT_TOUCH = 0x00000002

# --- STRUCTS (Strictly following your working example) ---
class POINTER_INFO(Structure):
    _fields_ = [
        ("pointerType", c_uint32),
        ("pointerId", c_uint32),
        ("frameId", c_uint32),
        ("pointerFlags", c_int),
        ("sourceDevice", HANDLE),
        ("hwndTarget", HWND),
        ("ptPixelLocation", POINT),
        ("ptHimetricLocation", POINT),
        ("ptPixelLocationRaw", POINT),
        ("ptHimetricLocationRaw", POINT),
        ("dwTime", DWORD),
        ("historyCount", c_uint32),
        ("inputData", c_int32),
        ("dwKeyStates", DWORD),
        ("PerformanceCount", c_uint64),
        ("ButtonChangeType", c_int)
    ]

class POINTER_TOUCH_INFO(Structure):
    _fields_ = [
        ("pointerInfo", POINTER_INFO),
        ("touchFlags", c_int),
        ("touchMask", c_int),
        ("rcContact", RECT),
        ("rcContactRaw", RECT),
        ("orientation", c_uint32),
        ("pressure", c_uint32)
    ]

# --- SETUP ---
user32 = ctypes.windll.user32
InitializeTouchInjection = getattr(user32, "InitializeTouchInjection", None)
InjectTouchInput = getattr(user32, "InjectTouchInput", None)

# --- GLOBAL STATE ---
TOUCH_AVAILABLE = False
MAX_TOUCHES = 2

# We keep a persistent object for every possible ID (0-9)
# so we can track state (UP/DOWN) for each finger independently.
touch_map = {} 

def initialize():
    global TOUCH_AVAILABLE, touch_map
    
    # Pre-allocate structs for IDs 0 to MAX_TOUCHES
    for i in range(MAX_TOUCHES):
        p_info = POINTER_INFO(pointerType=PT_TOUCH, pointerId=i, pointerFlags=POINTER_FLAG_NONE)
        t_info = POINTER_TOUCH_INFO(pointerInfo=p_info, touchMask=TOUCH_MASK_ALL)
        touch_map[i] = t_info

    if InitializeTouchInjection:
        # Initialize for max touches
        if InitializeTouchInjection(MAX_TOUCHES, 1): # 1 = TOUCH_FEEDBACK_DEFAULT
            TOUCH_AVAILABLE = True
            print("[Touch] Engine Initialized Successfully")
        else:
            print("[Touch] Initialize Failed")
    else:
        print("[Touch] API Not Found")

# Initialize on import
initialize()

def update_touch(pointer_id, x, y, is_down):
    """
    Updates the state of a specific pointer in our map.
    Does NOT inject yet.
    """
    if not TOUCH_AVAILABLE: return False
    
    if pointer_id >= MAX_TOUCHES: return False

    ti = touch_map[pointer_id]
    
    # Determine current state to calculate correct flags
    # We check if the previous flag had DOWN or INCONTACT
    was_down = (ti.pointerInfo.pointerFlags & POINTER_FLAG_INCONTACT) != 0

    if is_down:
        if not was_down:
            flags = POINTER_FLAG_DOWN | POINTER_FLAG_INRANGE | POINTER_FLAG_INCONTACT
        else:
            flags = POINTER_FLAG_UPDATE | POINTER_FLAG_INRANGE | POINTER_FLAG_INCONTACT
            
        ti.pointerInfo.ptPixelLocation.x = int(x)
        ti.pointerInfo.ptPixelLocation.y = int(y)
        
        # Update Contact Area (Simple 2px box)
        ti.rcContact.left = int(x) - 2
        ti.rcContact.right = int(x) + 2
        ti.rcContact.top = int(y) - 2
        ti.rcContact.bottom = int(y) + 2
        
        ti.pressure = 32000
        ti.orientation = 90
        ti.pointerInfo.pointerFlags = flags
        
    else:
        if was_down:
            # Transition to UP
            ti.pointerInfo.pointerFlags = POINTER_FLAG_UP
        else:
            # Already UP, reset to NONE so we don't send it
            ti.pointerInfo.pointerFlags = POINTER_FLAG_NONE

    return True

def process_frame():
    """
    Packs all active touches into a contiguous array and injects them.
    Must be called once per frame.
    """
    if not TOUCH_AVAILABLE: return False

    # 1. FILTER: Collect only touches that have actual flags (DOWN, UPDATE, UP)
    # We ignore any touch with POINTER_FLAG_NONE (0)
    active_contacts = []
    for i in range(MAX_TOUCHES):
        if touch_map[i].pointerInfo.pointerFlags != POINTER_FLAG_NONE:
            active_contacts.append(touch_map[i])

    count = len(active_contacts)
    if count == 0:
        return True

    # 2. PACK: Create a C-Array of exactly 'count' length
    # This solves Error 87. Windows receives a tight array with no "holes".
    contact_array = (POINTER_TOUCH_INFO * count)(*active_contacts)

    # 3. INJECT
    result = InjectTouchInput(count, byref(contact_array[0]))

    if result:
        # 4. CLEANUP: Reset UP flags to NONE
        # If we just sent an UP signal, next frame this finger should be invisible (NONE)
        for contact in active_contacts:
            if contact.pointerInfo.pointerFlags & POINTER_FLAG_UP:
                # Update the source map, not just the temp array
                touch_map[contact.pointerInfo.pointerId].pointerInfo.pointerFlags = POINTER_FLAG_NONE
        return True
    else:
        # Debugging Error 87
        err = ctypes.windll.kernel32.GetLastError()
        if err != 0:
            print(f"[Touch Error] Code: {err} | Count: {count}")
        return False