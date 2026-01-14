import cv2
import mediapipe as mp
import pyautogui
import math
import time
import config
import subprocess
import os
import winreg
import ctypes

# --- KEYBOARD COM SCRIPT ---
# This forces the Windows Tablet Keyboard to toggle properly
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

# --- CONFIGURATION ---
pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0

mp_hands = mp.solutions.hands
hands = None
pTime = 0
last_process_time = 0 

# --- STABILITY COUNTERS ---
pinky_frames = 0
middle_frames = 0
voice_frames = 0        
GESTURE_THRESHOLD = 5   

def fast_move(x, y):
    ctypes.windll.user32.SetCursorPos(int(x), int(y))

def get_dist_sq(p1, p2):
    return (p1[0] - p2[0])**2 + (p1[1] - p2[1])**2

def init_hand_tracking(complexity=0):
    global hands
    ensure_tablet_mode_enabled()
    hands = mp_hands.Hands(
        max_num_hands=1,
        model_complexity=complexity,
        min_detection_confidence=0.7,
        min_tracking_confidence=0.7
    )

def ensure_tablet_mode_enabled():
    try:
        key_path = r"Software\Microsoft\TabletTip\1.7"
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path) as key:
            winreg.SetValueEx(key, "EnableDesktopModeAutoInvoke", 0, winreg.REG_DWORD, 1)
    except Exception: pass

def map_range(x, in_min, in_max, out_min, out_max):
    val = (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min
    return max(out_min, min(out_max, val))

def toggle_keyboard():
    try:
        subprocess.run(["powershell", "-Command", PS_TOGGLE_SCRIPT], creationflags=subprocess.CREATE_NO_WINDOW)
        config.keyboard_open = not getattr(config, 'keyboard_open', False)
    except Exception: pass

def process_frame(img):
    global pTime, pinky_frames, middle_frames, voice_frames
    if not hands: return None if config.headless_mode else img

    # --- 1. FLIP FIRST ---
    img = cv2.flip(img, 1) 
    
    h, w, c = img.shape
    imgRGB = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    results = hands.process(imgRGB)

    config.hand_detected = False
    
    # Prepare display_img 
    display_img = None
    if not config.headless_mode:
        display_img = img 
        cTime = time.time()
        fps = 1 / (cTime - pTime) if (cTime - pTime) > 0 else 0
        pTime = cTime
        cv2.putText(display_img, f"FPS: {int(fps)}", (20, 50), cv2.FONT_HERSHEY_PLAIN, 2, (0, 255, 0), 2)

    if results.multi_hand_landmarks:
        for hand_landmarks in results.multi_hand_landmarks:
            lmList = []
            for lm in hand_landmarks.landmark:
                lmList.append([int(lm.x * w), int(lm.y * h)])

            if lmList:
                hand_size_sq = get_dist_sq(lmList[5], lmList[0])
                if hand_size_sq < 900: continue 
                
                config.hand_detected = True

                x_thumb, y_thumb = lmList[4]
                x_index_tip, y_index_tip = lmList[8]
                x_mid_pip, y_mid_pip = lmList[10]
                x_mid_tip, y_mid_tip = lmList[12]
                x_pinky_pip, y_pinky_pip = lmList[18]
                x_pinky_tip, y_pinky_tip = lmList[20]
                
                # --- A. MOVEMENT ---
                x3 = map_range(x_index_tip, config.SENSITIVITY, w - config.SENSITIVITY, 0, config.wScr)
                y3 = map_range(y_index_tip, config.SENSITIVITY, h - config.SENSITIVITY, 0, config.hScr)
                
                move_delta_sq = (x3 - config.plocX)**2 + (y3 - config.plocY)**2
                if move_delta_sq > 4.0:
                    clocX = config.plocX + (x3 - config.plocX) / config.SMOOTHING
                    clocY = config.plocY + (y3 - config.plocY) / config.SMOOTHING
                    try: fast_move(clocX, clocY)
                    except: pass
                    config.plocX, config.plocY = clocX, clocY

                # --- B. CLICK ---
                real_hand_size = math.sqrt(hand_size_sq)
                scale = 1.0 + ((real_hand_size / w / 0.15) - 1.0) * config.DEPTH_SCALE
                dist_sq = get_dist_sq(lmList[10], lmList[4]) 
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

                # --- C. GESTURES ---
                
                # Keyboard (Middle Finger Extended, Others Down)
                # Check: Tip above PIP, Tip above Index Tip, Tip above Ring Tip (16)
                if (y_mid_tip < y_mid_pip - 10) and (y_mid_tip < y_index_tip) and (y_mid_tip < lmList[16][1]):
                    middle_frames += 1
                else: 
                    middle_frames = 0
                
                if middle_frames > GESTURE_THRESHOLD and not getattr(config, 'pinky_triggered', False):
                    toggle_keyboard()
                    config.pinky_triggered = True
                elif middle_frames == 0: 
                    config.pinky_triggered = False

                # Right Click (Pinky)
                if (y_pinky_tip < y_pinky_pip - 10) and (y_pinky_tip < lmList[16][1]):
                    pinky_frames += 1
                else: 
                    pinky_frames = 0
                
                if pinky_frames > GESTURE_THRESHOLD and not config.right_clicked:
                    pyautogui.click(button='right')
                    config.right_clicked = True
                elif pinky_frames == 0: 
                    config.right_clicked = False

                # Voice (Thumb + Pinky)
                voice_dist_sq = get_dist_sq(lmList[20], lmList[4])
                config.voice_active_gesture = (voice_dist_sq < (config.CLICK_DIST * scale * 1.2)**2)

                # --- VISUALS ---
                if display_img is not None:
                    cv2.circle(display_img, (x_index_tip, y_index_tip), 8, (0, 255, 255), cv2.FILLED)
                    color = (0, 255, 0) if config.dragging else (0, 0, 255)
                    cv2.line(display_img, (x_thumb, y_thumb), (x_mid_pip, y_mid_pip), color, 2)
                    
                    if config.voice_active_gesture:
                         cv2.putText(display_img, "MIC ON", (x_thumb, y_thumb - 30), cv2.FONT_HERSHEY_PLAIN, 2, (255, 255, 0), 2)
                    if getattr(config, 'pinky_triggered', False):
                        cv2.putText(display_img, "KEYBOARD", (x_mid_tip, y_mid_tip-20), cv2.FONT_HERSHEY_PLAIN, 1.5, (255,0,255), 2)
                    if config.right_clicked:
                        cv2.putText(display_img, "R-CLICK", (x_pinky_tip, y_pinky_tip-20), cv2.FONT_HERSHEY_PLAIN, 1.5, (255,0,0), 2)

    # --- LEAK PROTECTION & IDLE VISUALS ---
    if not config.hand_detected:
        config.voice_active_gesture = False
        config.right_clicked = False
        config.pinky_triggered = False
        if display_img is not None:
             cv2.putText(display_img, "NO HAND", (w//2 - 50, h - 30), cv2.FONT_HERSHEY_PLAIN, 2, (100, 100, 100), 2)

    return display_img