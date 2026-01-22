import cv2
import mediapipe as mp
import math
import time
import config
import actions

# --- CONFIGURATION ---
mp_hands = mp.solutions.hands
hands = None
pTime = 0

# --- VOICE STABILITY ---
voice_grace = 0
VOICE_MAX_GRACE = 20 

# --- MIDDLE FINGER STABILITY ---
plocMidX, plocMidY = 0, 0
mid_track_active = False 

# HYSTERESIS VARIABLES
middle_grace = 0
MIDDLE_GRACE_MAX = 5  # Must hold straight for 5 frames to engage
is_dual_mode_active = False

def get_dist_sq(p1, p2):
    return (p1[0] - p2[0])**2 + (p1[1] - p2[1])**2

def init_hand_tracking(complexity=0):
    global hands
    print(f"[Tracking] Initializing Hand Tracking (Complexity: {complexity})...")
    hands = mp_hands.Hands(
        max_num_hands=1,
        model_complexity=complexity,
        min_detection_confidence=0.7,
        min_tracking_confidence=0.7
    )

def map_range(x, in_min, in_max, out_min, out_max):
    val = (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min
    return max(out_min, min(out_max, val))

def process_frame(img):
    global pTime, voice_grace
    global plocMidX, plocMidY, mid_track_active
    global middle_grace, is_dual_mode_active
    
    if not hands: 
        return None if config.headless_mode else img

    # --- 1. FLIP & PROCESS ---
    img = cv2.flip(img, 1) 
    h, w, c = img.shape
    imgRGB = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    results = hands.process(imgRGB)

    config.hand_detected = False
    gesture_seen_now = False

    # FPS Calc
    display_img = None
    if not config.headless_mode:
        display_img = img 
        cTime = time.time()
        fps = 1 / (cTime - pTime) if (cTime - pTime) > 0 else 0
        pTime = cTime
        cv2.putText(display_img, f"FPS: {int(fps)}", (20, 50), cv2.FONT_HERSHEY_PLAIN, 2, (0, 255, 0), 2)

    # --- CALCULATE 16:9 ACTIVE ZONE ---
    avail_w = w - (2 * config.SENSITIVITY)
    avail_h = h - (2 * config.SENSITIVITY)
    if avail_w < 10: avail_w = 10
    if avail_h < 10: avail_h = 10

    target_ratio = 16 / 9
    box_w = avail_w
    box_h = box_w / target_ratio
    if box_h > avail_h:
        box_h = avail_h
        box_w = box_h * target_ratio

    center_x = (w // 2) + config.BOX_OFFSET_X
    center_y = (h // 2) + config.BOX_OFFSET_Y
    half_w = int(box_w / 2)
    half_h = int(box_h / 2)

    x_min = center_x - half_w
    x_max = center_x + half_w
    y_min = center_y - half_h
    y_max = center_y + half_h
    # ------------------------------------

    if results.multi_hand_landmarks:
        for hand_landmarks in results.multi_hand_landmarks:
            lmList = []
            for lm in hand_landmarks.landmark:
                lmList.append([int(lm.x * w), int(lm.y * h)])

            if lmList:
                hand_size_sq = get_dist_sq(lmList[5], lmList[0])
                if hand_size_sq < 900: continue 
                
                config.hand_detected = True

                # Key Landmarks
                x_thumb, y_thumb = lmList[4]
                x_index_tip, y_index_tip = lmList[8]
                x_mid_pip, y_mid_pip = lmList[10]
                x_mid_tip, y_mid_tip = lmList[12]
                x_pinky_pip, y_pinky_pip = lmList[18]
                x_pinky_tip, y_pinky_tip = lmList[20]
                
                # --- A. DETECT GESTURES ---
                
                # 1. Middle Finger Straight? (Tip above PIP)
                raw_middle_straight = (y_mid_tip < y_mid_pip - 10) and (y_mid_tip < y_index_tip)
                
                # STABILITY LOGIC:
                if raw_middle_straight:
                    if middle_grace < MIDDLE_GRACE_MAX:
                        middle_grace += 1
                else:
                    if middle_grace > 0:
                        middle_grace -= 1
                
                # Only activate Dual Mode if we are saturated
                is_dual_mode_active = (middle_grace >= MIDDLE_GRACE_MAX)
                
                # 2. Pinky Finger Straight? (Keyboard Toggle)
                is_pinky_straight = (y_pinky_tip < y_pinky_pip - 10)
                config.pinky_bent = is_pinky_straight

                # --- B. INDEX FINGER LOCATION ---
                x3 = map_range(x_index_tip, x_min, x_max, 0, config.wScr)
                y3 = map_range(y_index_tip, y_min, y_max, 0, config.hScr)
                
                move_delta_sq = (x3 - config.plocX)**2 + (y3 - config.plocY)**2
                if move_delta_sq > 4.0:
                    clocX = config.plocX + (x3 - config.plocX) / config.SMOOTHING
                    clocY = config.plocY + (y3 - config.plocY) / config.SMOOTHING
                else:
                    clocX, clocY = config.plocX, config.plocY
                config.plocX, config.plocY = clocX, clocY

                # --- C. MIDDLE FINGER LOCATION (Conditional) ---
                clocMidX, clocMidY = 0, 0
                
                if is_dual_mode_active:
                    mx3 = map_range(x_mid_tip, x_min, x_max, 0, config.wScr)
                    my3 = map_range(y_mid_tip, y_min, y_max, 0, config.hScr)
                    
                    if not mid_track_active:
                         plocMidX, plocMidY = mx3, my3
                    
                    mid_track_active = True
                    
                    mid_delta_sq = (mx3 - plocMidX)**2 + (my3 - plocMidY)**2
                    if mid_delta_sq > 4.0:
                        clocMidX = plocMidX + (mx3 - plocMidX) / config.SMOOTHING
                        clocMidY = plocMidY + (my3 - plocMidY) / config.SMOOTHING
                    else:
                        clocMidX, clocMidY = plocMidX, plocMidY
                    plocMidX, plocMidY = clocMidX, clocMidY
                else:
                    mid_track_active = False

                # --- D. PINCH DETECTION ---
                real_hand_size = math.sqrt(hand_size_sq)
                scale = 1.0 + ((real_hand_size / w / 0.15) - 1.0) * config.DEPTH_SCALE
                dist_sq = get_dist_sq(lmList[10], lmList[4]) 
                active_thresh_sq = (config.CLICK_DIST * scale)**2
                release_thresh_sq = (config.RELEASE_DIST * scale)**2

                if not config.dragging:
                    if dist_sq < active_thresh_sq:
                        config.dragging = True 
                else:
                    if dist_sq > release_thresh_sq:
                        config.dragging = False 
                
                # --- E. EXECUTE ACTIONS ---
                actions.handle_input(
                    clocX, clocY,           
                    clocMidX, clocMidY,     
                    config.dragging,        
                    is_dual_mode_active # <--- Now uses the Stabilized Boolean
                )

                # --- VOICE ---
                voice_dist_sq = get_dist_sq(lmList[20], lmList[4])
                gesture_seen_now = (voice_dist_sq < (config.CLICK_DIST * scale * 1.2)**2)

                # --- VISUALS ---
                if display_img is not None:
                    # Box
                    draw_x1 = int(max(0, min(w, x_min)))
                    draw_y1 = int(max(0, min(h, y_min)))
                    draw_x2 = int(max(0, min(w, x_max)))
                    draw_y2 = int(max(0, min(h, y_max)))
                    cv2.rectangle(display_img, (draw_x1, draw_y1), (draw_x2, draw_y2), (255, 255, 255), 2)

                    # Index
                    cv2.circle(display_img, (x_index_tip, y_index_tip), 8, (0, 255, 255), cv2.FILLED)
                    
                    # Middle (Only draw if active)
                    if is_dual_mode_active:
                        cv2.circle(display_img, (x_mid_tip, y_mid_tip), 8, (255, 0, 0), cv2.FILLED)

                    # Pinch Line
                    color = (0, 255, 0) if config.dragging else (0, 0, 255)
                    cv2.line(display_img, (x_thumb, y_thumb), (x_mid_pip, y_mid_pip), color, 2)
                    
                    if getattr(config, 'keyboard_triggered', False):
                        cv2.putText(display_img, "KEYBOARD", (x_mid_tip, y_mid_tip-20), cv2.FONT_HERSHEY_PLAIN, 1.5, (255,0,255), 2)

    # --- VOICE HYSTERESIS ---
    if gesture_seen_now:
        voice_grace = VOICE_MAX_GRACE
    else:
        if voice_grace > 0:
            voice_grace -= 1
    config.voice_active_gesture = (voice_grace > 0)

    if display_img is not None and config.voice_active_gesture:
         cv2.putText(display_img, "MIC ON", (50, 100), cv2.FONT_HERSHEY_PLAIN, 3, (0, 255, 255), 3)

    # --- IDLE VISUALS ---
    if not config.hand_detected:
        config.keyboard_triggered = False
        actions.release_all()

        if display_img is not None:
             cv2.putText(display_img, "NO HAND", (w//2 - 50, h - 30), cv2.FONT_HERSHEY_PLAIN, 2, (100, 100, 100), 2)
             d_x1 = int(max(0, min(w, center_x - half_w)))
             d_y1 = int(max(0, min(h, center_y - half_h)))
             d_x2 = int(max(0, min(w, center_x + half_w)))
             d_y2 = int(max(0, min(h, center_y + half_h)))
             cv2.rectangle(display_img, (d_x1, d_y1), (d_x2, d_y2), (255, 255, 255), 2)

    return display_img