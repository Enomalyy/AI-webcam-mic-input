import cv2
import mediapipe as mp
import pyautogui
import math
import time
import config
import subprocess
import os
import winreg
import ctypes  # For fast mouse movement

# --- CONFIGURATION ---
pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0

mp_hands = mp.solutions.hands
hands = None
pTime = 0

# --- STABILITY COUNTERS ---
pinky_frames = 0
middle_frames = 0
voice_frames = 0       
GESTURE_THRESHOLD = 5 

# --- KEYBOARD COM SCRIPT ---
PS_TOGGLE_SCRIPT = r"""
$code = @'
using System;
using System.Diagnostics;
using System.Runtime.InteropServices;
public class TouchKeyboardController {
    [ComImport, Guid("4ce576fa-83dc-4F88-951c-9d0782b4e376")] class UIHostNoLaunch {}
    [ComImport, Guid("37c994e7-432b-4834-a2f7-dce1f13b834b")] [InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    interface ITipInvocation { void Toggle(IntPtr hwnd); }
    [DllImport("user32.dll", SetLastError = false)] static extern IntPtr GetDesktopWindow();
    public static void Toggle() {
        try {
            UIHostNoLaunch uiHost = new UIHostNoLaunch();
            ((ITipInvocation)uiHost).Toggle(GetDesktopWindow());
            Marshal.ReleaseComObject(uiHost);
        } catch (COMException) {
            Process.Start(new ProcessStartInfo("TabTip.exe") { UseShellExecute = true });
        }
    }
}
'@
Add-Type -TypeDefinition $code -Language CSharp
[TouchKeyboardController]::Toggle()
"""

# --- FAST MOUSE MOVEMENT ---
def fast_move(x, y):
    """Moves mouse using low-level Windows API (Instant)"""
    ctypes.windll.user32.SetCursorPos(int(x), int(y))

# --- MATH HELPER ---
def get_dist_sq(p1, p2):
    """Returns squared Euclidean distance (No Square Root = Faster)"""
    return (p1[0] - p2[0])**2 + (p1[1] - p2[1])**2

def init_hand_tracking(complexity=0):
    global hands
    ensure_tablet_mode_enabled()
    hands = mp_hands.Hands(
        max_num_hands=1,
        model_complexity=complexity,
        min_detection_confidence=0.8,
        min_tracking_confidence=0.8
    )

def ensure_tablet_mode_enabled():
    try:
        key_path = r"Software\Microsoft\TabletTip\1.7"
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path) as key:
            winreg.SetValueEx(key, "EnableDesktopModeAutoInvoke", 0, winreg.REG_DWORD, 1)
    except Exception as e:
        print(f"Registry Error: {e}")

def map_range(x, in_min, in_max, out_min, out_max):
    val = (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min
    return max(out_min, min(out_max, val))

def toggle_keyboard():
    try:
        subprocess.run(["powershell", "-Command", PS_TOGGLE_SCRIPT], creationflags=subprocess.CREATE_NO_WINDOW)
        config.keyboard_open = not config.keyboard_open
    except Exception: pass

def process_frame(img):
    global pTime, pinky_frames, middle_frames, voice_frames
    if not hands: return img

    h, w, c = img.shape
    imgRGB = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    imgRGB = cv2.flip(imgRGB, 1)
    results = hands.process(imgRGB)
    display_img = cv2.flip(img, 1) if not config.headless_mode else None

    # Visuals: FPS
    if display_img is not None:
        cTime = time.time()
        fps = 1 / (cTime - pTime) if (cTime - pTime) > 0 else 0
        pTime = cTime
        cv2.putText(display_img, f"FPS: {int(fps)}", (20, 50), cv2.FONT_HERSHEY_PLAIN, 2, (0, 255, 0), 2)

    valid_hand_found = False

    if results.multi_hand_landmarks:
        for hand_landmarks in results.multi_hand_landmarks:
            lmList = []
            for lm in hand_landmarks.landmark:
                lmList.append([int(lm.x * w), int(lm.y * h)])

            if lmList:
                # 1. SIZE CHECK (SQUARED)
                # Wrist(0) to Index Knuckle(5)
                # 30px size threshold -> 900 squared
                hand_size_sq = get_dist_sq(lmList[5], lmList[0])
                if hand_size_sq < 900: 
                    continue 
                
                valid_hand_found = True

                x_thumb, y_thumb = lmList[4]
                x_index_tip, y_index_tip = lmList[8]
                x_mid_pip, y_mid_pip = lmList[10]
                x_mid_tip, y_mid_tip = lmList[12]
                x_ring_tip, y_ring_tip = lmList[16]
                x_pinky_pip, y_pinky_pip = lmList[18]
                x_pinky_tip, y_pinky_tip = lmList[20]
                
                # A. MOVEMENT (Index)
                x3 = map_range(x_index_tip, config.SENSITIVITY, w - config.SENSITIVITY, 0, config.wScr)
                y3 = map_range(y_index_tip, config.SENSITIVITY, h - config.SENSITIVITY, 0, config.hScr)
                
                # Check movement delta squared (2.0 pixels -> 4.0 squared)
                move_delta_sq = (x3 - config.plocX)**2 + (y3 - config.plocY)**2
                
                if move_delta_sq > 4.0:
                    clocX = config.plocX + (x3 - config.plocX) / config.SMOOTHING
                    clocY = config.plocY + (y3 - config.plocY) / config.SMOOTHING
                    
                    # USE FAST CTYPES MOVE
                    try: fast_move(clocX, clocY)
                    except: pass
                    
                    config.plocX, config.plocY = clocX, clocY

                # B. CLICK (Thumb -> Mid PIP)
                # We need the real square root for scaling factor (linear math), 
                # but we use squared distances for the threshold check.
                real_hand_size = math.sqrt(hand_size_sq)
                scale = 1.0 + ((real_hand_size / w / 0.15) - 1.0) * config.DEPTH_SCALE
                
                dist_sq = get_dist_sq(lmList[10], lmList[4]) # Mid PIP to Thumb Tip
                click_thresh_sq = (config.CLICK_DIST * scale)**2
                release_thresh_sq = (config.RELEASE_DIST * scale)**2

                if not config.dragging:
                    if dist_sq < click_thresh_sq:
                        pyautogui.mouseDown()
                        config.dragging = True
                else:
                    if dist_sq > release_thresh_sq:
                        pyautogui.mouseUp()
                        config.dragging = False

                # C. KEYBOARD (Middle Finger)
                # Logic: Tip below PIP (folded) or Tip above Neighbors?
                # Original logic: Tip (12) higher (lower y) than PIP (10) AND Neighbors (8, 16)
                if (y_mid_tip < y_mid_pip - 10) and (y_mid_tip < y_index_tip) and (y_mid_tip < y_ring_tip):
                    middle_frames += 1
                else: middle_frames = 0
                
                if middle_frames > GESTURE_THRESHOLD and not config.pinky_triggered:
                    toggle_keyboard()
                    config.pinky_triggered = True
                elif middle_frames == 0: config.pinky_triggered = False

                # D. RIGHT CLICK (Pinky Finger)
                # Logic: Tip (20) higher than PIP (18) and Ring Tip (16)
                if (y_pinky_tip < y_pinky_pip - 10) and (y_pinky_tip < y_ring_tip):
                    pinky_frames += 1
                else: pinky_frames = 0
                
                if pinky_frames > GESTURE_THRESHOLD and not config.right_clicked:
                    pyautogui.click(button='right')
                    config.right_clicked = True
                elif pinky_frames == 0: config.right_clicked = False

                # E. VOICE (Thumb + Pinky)
                voice_dist_sq = get_dist_sq(lmList[20], lmList[4])
                voice_thresh_sq = (config.CLICK_DIST * scale * 1.2)**2
                
                if voice_dist_sq < voice_thresh_sq: 
                    voice_frames += 1
                else: 
                    voice_frames = 0
                
                config.voice_active_gesture = (voice_frames > GESTURE_THRESHOLD)

                # VISUALS
                if display_img is not None:
                    cv2.circle(display_img, (x_index_tip, y_index_tip), 8, (0, 255, 255), cv2.FILLED)
                    color = (0, 255, 0) if config.dragging else (0, 0, 255)
                    cv2.line(display_img, (x_thumb, y_thumb), (x_mid_pip, y_mid_pip), color, 2)
                    
                    if config.voice_active_gesture:
                         cv2.line(display_img, (x_thumb, y_thumb), (x_pinky_tip, y_pinky_tip), (255, 255, 0), 3)
                         cv2.putText(display_img, "MIC ON", (x_thumb, y_thumb - 30), cv2.FONT_HERSHEY_PLAIN, 2, (255, 255, 0), 2)
                    
                    if config.pinky_triggered:
                        cv2.putText(display_img, "KEYBOARD", (x_mid_tip, y_mid_tip-20), cv2.FONT_HERSHEY_PLAIN, 1.5, (255,0,255), 2)
                    
                    if config.right_clicked:
                        cv2.putText(display_img, "R-CLICK", (x_pinky_tip, y_pinky_tip-20), cv2.FONT_HERSHEY_PLAIN, 1.5, (255,0,0), 2)

    # --- LEAK PROTECTION ---
    if not valid_hand_found:
        voice_frames = 0
        config.voice_active_gesture = False
        pinky_frames = 0
        middle_frames = 0
        config.right_clicked = False
        config.pinky_triggered = False
        if display_img is not None:
             cv2.putText(display_img, "NO HAND", (w//2 - 50, h - 30), cv2.FONT_HERSHEY_PLAIN, 2, (100, 100, 100), 2)

    return display_img