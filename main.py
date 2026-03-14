import cv2
import time
import datetime
import threading
import serial
import numpy as np
from collections import deque
from scipy.signal import butter, filtfilt, find_peaks

# Project FEAT Core Modules
try:
    from core.ai_engine import AIEngine
    from core.defense_shield import DefenseShield
    HAS_CORE = True
except ImportError as e:
    print(f"[ERROR] Could not load core modules. Ensure 'core' directory exists. {e}")
    HAS_CORE = False

# --- rPPG Configuration ---
BUFFER_SIZE = 150 # Stores ~5 seconds of frames at 30fps
MIN_BPM = 50.0
MAX_BPM = 180.0

def butter_bandpass(lowcut, highcut, fs, order=5):
    nyq = 0.5 * fs
    low = lowcut / nyq
    high = highcut / nyq
    b, a = butter(order, [low, high], btype='band')
    return b, a

def apply_filter(data, fs):
    b, a = butter_bandpass(MIN_BPM/60.0, MAX_BPM/60.0, fs, order=3)
    y = filtfilt(b, a, data)
    return y

# --- Vision Utilities ---
def night_vision(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    return cv2.merge([np.zeros_like(gray), gray, np.zeros_like(gray)])

def thermal_view(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    return cv2.applyColorMap(gray, cv2.COLORMAP_INFERNO)

def get_threat_level(num_targets, motion_score):
    score = num_targets * 20
    if motion_score > 5000:
        score += 40
    elif motion_score > 500:
        score += 20
    if score >= 80:
        return "CRITICAL", (0, 0, 255)
    elif score >= 50:
        return "HIGH", (0, 100, 255)
    elif score >= 20:
        return "MEDIUM", (0, 165, 255)
    else:
        return "LOW", (0, 255, 0)

def main():
    print("\n[INIT] Booting Project FEAT Edge Node...")
    boot_text = [
        "INITIALIZING KERNEL...",
        "LOADING NEURAL WEIGHTS...",
        "CONNECTING TO EDGE SENSOR...",
        "BYPASSING SECURITY PROTOCOLS...",
        "SYSTEM ONLINE."
    ]
    for text in boot_text:
        print(f"> {text}")
        time.sleep(0.4)
    print("\n")
    
    # Initialize Core Engines
    ai = AIEngine() if HAS_CORE else None
    shield = DefenseShield() if HAS_CORE else None

    # --- Hardware Link Setup (Arduino Biometrics) ---
    SERIAL_PORT = 'COM3' 
    BAUD_RATE = 115200

    try:
        arduino = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.05)
        print("FEAT SYSTEM: Biometric Hardware Link ESTABLISHED.")
        time.sleep(2) # Give the Arduino a second to reset upon connection
    except Exception as e:
        arduino = None
        print(f"FEAT SYSTEM WARNING: Hardware Link FAILED. Check port ({SERIAL_PORT}).")

    # Data buffer for sliding graph
    GRAPH_POINTS = 100
    hw_sensor_data = deque([0] * GRAPH_POINTS, maxlen=GRAPH_POINTS)
    hw_times = deque([0] * GRAPH_POINTS, maxlen=GRAPH_POINTS)
    
    # BPM Calculation Variables
    last_beat_time = time.time()
    bpm_values = deque(maxlen=10) # Average the last 10 beats for a stable number
    hw_current_bpm = 0
    is_peaking = False
    
    hw_bio_mode = False # Separate mode for Arduino ECG
    
    # Initialize Haar Cascade for fast, lightweight face detection (for rPPG)
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

    # 0 = Built-in laptop cam, 1 or 2 = External Logitech Brio 101
    CAMERA_INDEX = 1  
    cap = cv2.VideoCapture(CAMERA_INDEX) # Removed CAP_DSHOW, letting OpenCV auto-detect backend
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    ret, frame1 = cap.read()
    ret, frame2 = cap.read()
    if not ret:
        print("[ERROR] Camera feed not detected. Check connections.")
        return

    prev_time = 0
    frame_count = 0
    
    # Modes
    night_mode = False
    thermal_mode = False
    camo_mode = False
    bio_mode = False # Biometric rPPG Scanner
    
    # Persistent State to prevent HUD flickering
    target_count = 0
    current_detections = []
    ai_status = "SECURE"
    ai_status_color = (0, 255, 0)
    ai_target_count = 0
    
    # rPPG Data buffers
    times = deque(maxlen=BUFFER_SIZE)
    green_signal = deque(maxlen=BUFFER_SIZE)
    current_bpm = 0

    # --- AI Multithreading Setup ---
    ai_frame = None
    ai_lock = threading.Lock()
    
    def ai_worker():
        nonlocal current_detections, ai_status, ai_status_color, ai_target_count, ai_frame
        while True:
            if ai_frame is not None and ai:
                with ai_lock:
                    frame_to_process = ai_frame.copy()
                
                ai_results = ai.detect(frame_to_process)
                detections = ai.get_detections(ai_results)
                
                # Check if any of the detections are classified as actual threats
                active_threats = sum(1 for d in detections if d.get("is_threat", False))
                
                with ai_lock:
                    current_detections = detections
                    ai_target_count = len(current_detections)
                    if active_threats > 0:
                        ai_status = f"PROXIMITY THREAT ({active_threats})"
                        ai_status_color = (0, 0, 255) # Red
                    elif ai_target_count > 0:
                        ai_status = "STABLE (BYSTANDERS)"
                        ai_status_color = (0, 255, 0) # Green
                    else:
                        ai_status = "SECURE"
                        ai_status_color = (0, 255, 0) # Green
            time.sleep(0.05) # Yield to main thread
            
    if HAS_CORE:
        threading.Thread(target=ai_worker, daemon=True).start()

    print("[SYSTEM] FEAT HUD Active.")
    print("  N = Night Vision | T = Thermal | C = Camo | B = Camera rPPG Bio | H = Hardware Bio | Q = Quit")

    while cap.isOpened():
        # --- VISION MODES START ---
        display_frame = frame1.copy()

        if night_mode:
            display_frame = night_vision(display_frame)
        elif thermal_mode:
            display_frame = thermal_view(display_frame)

        base_clean_frame = display_frame.copy() # Keep background untouched for Ghost HUD blend

        # Shield: Camo + Adversarial Detection
        is_adv = False
        adv_score = 0.0
        clean_frame = display_frame
        
        if shield:
            # Check for adversarial attack
            is_adv, adv_score = shield.is_adversarial(display_frame)
            if is_adv:
                cv2.putText(display_frame, f"!! ADVERSARIAL PATCH DETECTED {adv_score}",
                            (10, 180), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                
            if camo_mode:
                display_frame = shield.detect_camo(display_frame)
            
            # Sanitize frame for AI
            clean_frame = shield.sanitize(display_frame.copy())

        # --- MOTION / THREAT DETECTION ---
        diff = cv2.absdiff(frame1, frame2)
        gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        _, thresh = cv2.threshold(blur, 25, 255, cv2.THRESH_BINARY)
        dilated = cv2.dilate(thresh, None, iterations=3)
        contours, _ = cv2.findContours(dilated, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

        motion_score = 0
        motion_count = 0
        status = "SECURE"
        status_color = (0, 255, 0)
        
        # --- SLOW MOVEMENT / TARGET LOCK DETECTION ---
        for contour in contours:
            # INCREASED threshold: Ignore small jitters, only care about distinct movement
            if cv2.contourArea(contour) < 5000:
                continue
            motion_score += cv2.contourArea(contour)
            motion_count += 1
            
            (mx, my, mw, mh) = cv2.boundingRect(contour)
            # Draw motion target lock box with corner brackets for style
            cv2.line(display_frame, (mx, my), (mx + 20, my), (0, 165, 255), 2)
            cv2.line(display_frame, (mx, my), (mx, my + 20), (0, 165, 255), 2)
            cv2.line(display_frame, (mx + mw, my + mh), (mx + mw - 20, my + mh), (0, 165, 255), 2)
            cv2.line(display_frame, (mx + mw, my + mh), (mx + mw, my + mh - 20), (0, 165, 255), 2)
            cv2.putText(display_frame, f"MOTION LCK", (mx, my - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 165, 255), 1)

        # Merge motion into status
        if motion_count > 0:
            status = "MOTION DETECTED"
            status_color = (0, 165, 255)

        # --- SLOW MOVEMENT DETECTION ---
        if 500 < motion_score <= 5000:
            cv2.putText(display_frame, "!! SLOW MOVEMENT DETECTED !!",
                        (10, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 165, 255), 2)

        # --- AI ENGINE DETECTION (THREADED) ---
        with ai_lock:
            # Pass the latest sanitized frame to the AI thread
            ai_frame = clean_frame
            # Grab the latest results from the background thread smoothly
            local_detections = list(current_detections)
            local_ai_status = ai_status
            local_ai_status_color = ai_status_color
            local_ai_target_count = ai_target_count

        # Override with AI threat if present, else keep motion status
        if "THREAT" in local_ai_status:
            status = local_ai_status
            status_color = local_ai_status_color

        target_count = motion_count + local_ai_target_count
        
        # Display AI bounding boxes smoothly on EVERY frame
        for d in local_detections:
            x1, y1, x2, y2 = d["bbox"]
            is_threat = d.get("is_threat", False)
            
            # Choose color based on threat assessment
            box_color = (0, 0, 255) if is_threat else (0, 255, 0)
            
            # Draw AI box
            cv2.rectangle(display_frame, (x1, y1), (x2, y2), box_color, 2)
            # Add a slight dark background for text to make it stable and readable
            # Draw a bit wider box for the threat text
            bg_width = 300 if is_threat else 180
            cv2.rectangle(display_frame, (x1, y1 - 20), (x1 + bg_width, y1), (0, 0, 0), -1)
            cv2.putText(display_frame,
                        f"{d['label']} {d['conf']:.0%} | {d['distance']}m | {d['zone']}",
                        (x1 + 5, y1 - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, box_color, 1)

        # --- BIOMETRIC SCANNER (rPPG) ---
        if bio_mode:
            gray_bio = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray_bio, 1.3, 5)

            if len(faces) > 0:
                (x, y, w, h) = faces[0]
                
                # 1. Isolate the Forehead
                fh_x = int(x + (w * 0.25))
                fh_y = int(y + (h * 0.05))
                fh_w = int(w * 0.5)
                fh_h = int(h * 0.15)
                
                # Draw target lock
                cv2.rectangle(display_frame, (x, y), (x+w, y+h), (0, 0, 255), 2)
                cv2.rectangle(display_frame, (fh_x, fh_y), (fh_x+fh_w, fh_y+fh_h), (0, 255, 0), 2)
                cv2.putText(display_frame, "BIO-LOCK", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

                # 2. Extract Green Channel
                forehead_roi = frame1[fh_y:fh_y+fh_h, fh_x:fh_x+fh_w]
                if forehead_roi.size > 0:
                    green_channel = forehead_roi[:, :, 1] 
                    mean_green = np.mean(green_channel)
                    green_signal.append(mean_green)
                    times.append(time.time())

                # 3. Process Signal
                if len(green_signal) == BUFFER_SIZE:
                    time_diff = times[-1] - times[0]
                    if time_diff > 0:
                        actual_fps = BUFFER_SIZE / time_diff
                        detrended_signal = np.diff(green_signal)
                        try:
                            filtered_signal = apply_filter(detrended_signal, actual_fps)
                            fft_data = np.abs(np.fft.rfft(filtered_signal))
                            fft_freqs = np.fft.rfftfreq(len(filtered_signal), 1.0/actual_fps)
                            valid_indices = np.where((fft_freqs >= MIN_BPM/60.0) & (fft_freqs <= MAX_BPM/60.0))
                            if len(valid_indices[0]) > 0:
                                valid_fft = fft_data[valid_indices]
                                valid_freqs = fft_freqs[valid_indices]
                                peak_idx = np.argmax(valid_fft)
                                dominant_freq = valid_freqs[peak_idx]
                                current_bpm = int(dominant_freq * 60.0)
                        except Exception as e:
                            pass 

            # Biometric HUD Overlay
            bio_text_y = 400 # Fixed position for stability
            
            # BIOMETRIC THREAT LOGIC: High heartrate indicates stress/deception/threat
            is_bio_threat = False
            
            if len(green_signal) < BUFFER_SIZE:
                status_text = f"CALIBRATING BIO... {int((len(green_signal)/BUFFER_SIZE)*100)}%"
                color = (0, 255, 255) # Yellow
            else:
                if current_bpm > 100: # Elevated heart rate threshold
                    status_text = f"HEART RATE: {current_bpm} BPM (ELEVATED: THREAT)"
                    color = (0, 0, 255) # Red
                    is_bio_threat = True
                else:
                    status_text = f"HEART RATE: {current_bpm} BPM (NORMAL)"
                    color = (0, 255, 0) # Green
            
            cv2.putText(display_frame, status_text, (10, bio_text_y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
            
            # Escalation: If Biometrics detect a threat, override main HUD status
            if is_bio_threat:
                status = "BIOMETRIC ANOMALY"
                status_color = (0, 0, 255)

        else:
            # Clear buffers if mode turned off
            green_signal.clear()
            times.clear()

        # --- HARDWARE BIOMETRIC READ & DRAW (Arduino) ---
        if arduino and arduino.in_waiting > 0:
            try:
                line = arduino.readline().decode('utf-8').strip()
                if line:
                    val = float(line)
                    hw_sensor_data.append(val)
                    hw_times.append(time.time())
            except Exception as e:
                pass # Ignore serial garbage

        if hw_bio_mode:
            # Define where the graph sits on your HUD
            graph_x, graph_y = 30, 150 
            graph_w, graph_h = 250, 100
            
            # Draw the boundary box and label
            cv2.rectangle(display_frame, (graph_x, graph_y), (graph_x + graph_w, graph_y + graph_h), (0, 255, 0), 1)
            cv2.putText(display_frame, "LIVE HARDWARE BIO-FEED", (graph_x, graph_y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        
            data_min = min(hw_sensor_data)
            data_max = max(hw_sensor_data)
            
            # Only draw the wave if we have actual fluctuating data
            if data_max - data_min > 0: 
                # Normalize the raw LDR values to fit the height of our drawn box
                normalized_data = [
                    int(graph_h - ((x - data_min) / (data_max - data_min) * graph_h))
                    for x in hw_sensor_data
                ]
                
                # Plot the connected lines to create the wave
                for i in range(1, len(normalized_data)):
                    x1 = graph_x + int((i - 1) * (graph_w / GRAPH_POINTS))
                    y1 = graph_y + normalized_data[i - 1]
                    x2 = graph_x + int(i * (graph_w / GRAPH_POINTS))
                    y2 = graph_y + normalized_data[i]
                    
                    # Draw the line segment (Cyan color)
                    cv2.line(display_frame, (x1, y1), (x2, y2), (255, 255, 0), 2)
                
                # --- Dynamic Peak Finding for Hardware BPM ---
                local_avg = np.mean(hw_sensor_data)
                local_max = np.max(hw_sensor_data)
                
                # Set a dynamic threshold halfway between the average and the highest peak
                threshold = local_avg + (local_max - local_avg) * 0.5 
                
                latest_val = hw_sensor_data[-1]
                
                # If the wave crosses our threshold going up...
                if latest_val > threshold and not is_peaking:
                    is_peaking = True
                    current_time = time.time()
                    time_diff = current_time - last_beat_time
                    
                    # Filter out noise (only accept beats between 40 and 200 BPM)
                    if 0.3 < time_diff < 1.5: 
                        raw_bpm = 60.0 / time_diff
                        bpm_values.append(raw_bpm)
                        # Average it out so the display is smooth
                        hw_current_bpm = int(np.mean(bpm_values)) 
                        
                    last_beat_time = current_time
                    
                # Reset the peak detector when the wave drops back below average
                elif latest_val < local_avg: 
                    is_peaking = False

            # Display computed BPM next to the graph
            if hw_current_bpm > 0:
                cv2.putText(display_frame, f"HEART RATE: {hw_current_bpm} BPM", (graph_x, graph_y - 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
            else:
                cv2.putText(display_frame, "HEART RATE: CALIBRATING...", (graph_x, graph_y - 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 165, 255), 1)

        # --- THREAT LEVEL ---
        threat_level, threat_color = get_threat_level(target_count, motion_score)

        # --- HUD RENDERING ---
        height, width = display_frame.shape[:2]

        # Crosshair
        cx, cy = width // 2, height // 2
        cv2.line(display_frame, (cx - 20, cy), (cx + 20, cy), (0, 255, 0), 1)
        cv2.line(display_frame, (cx, cy - 20), (cx, cy + 20), (0, 255, 0), 1)
        cv2.circle(display_frame, (cx, cy), 10, (0, 255, 0), 1)

        # Border glow
        border_color = (0, 0, 255) if status == "THREAT DETECTED" else (0, 255, 0)
        cv2.rectangle(display_frame, (3, 3), (width - 3, height - 3), border_color, 3)

        # FPS calculation
        current_time = time.time()
        fps = 1 / (current_time - prev_time) if prev_time else 0
        prev_time = current_time

        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Active modes string
        active_modes = []
        if night_mode: active_modes.append("NIGHT")
        elif thermal_mode: active_modes.append("THERMAL")
        else: active_modes.append("NORMAL")
        if camo_mode: active_modes.append("+CAMO")
        if bio_mode: active_modes.append("+rPPG")
        if hw_bio_mode: active_modes.append("+HW_BIO")
        mode_text = " ".join(active_modes)

        # HUD Text Left
        cv2.putText(display_frame, "FEAT OS v0.3", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        cv2.putText(display_frame, f"STATUS: {status}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, status_color, 2)
        cv2.putText(display_frame, f"THREAT: {threat_level}", (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, threat_color, 2)
        cv2.putText(display_frame, f"TARGETS: {target_count}", (10, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        
        # HUD Text Bottom/Right
        cv2.putText(display_frame, f"MODE: {mode_text}", (10, height - 50), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
        cv2.putText(display_frame, f"FPS: {int(fps)}", (width - 100, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        cv2.putText(display_frame, timestamp, (10, height - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

        # --- DISPLAY ---
        # Apply Ghost HUD effect (Alpha Blend: 70% HUD, 30% Original Background)
        cv2.addWeighted(display_frame, 0.7, base_clean_frame, 0.3, 0, display_frame)
        
        cv2.imshow("Project FEAT - Tactical HUD", display_frame)

        frame1 = frame2
        ret, frame2 = cap.read()

        # Keyboard Controls
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('n'):
            night_mode = not night_mode
            thermal_mode = False
            print(f"[MODE] Night Vision: {night_mode}")
        elif key == ord('t'):
            thermal_mode = not thermal_mode
            night_mode = False
            print(f"[MODE] Thermal: {thermal_mode}")
        elif key == ord('c'):
            camo_mode = not camo_mode
            print(f"[MODE] Camo Detection: {camo_mode}")
        elif key == ord('b'):
            bio_mode = not bio_mode
            print(f"[MODE] Camera rPPG Scanner: {bio_mode}")
        elif key == ord('h'):
            hw_bio_mode = not hw_bio_mode
            print(f"[MODE] Hardware Bio Scanner: {hw_bio_mode}")

    if arduino:
        arduino.close()
    cap.release()
    cv2.destroyAllWindows()
    print("[SYSTEM] Shutting down...")

if __name__ == "__main__":
    main()