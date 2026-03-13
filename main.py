import cv2
import time
import datetime
import numpy as np

def night_vision(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    return cv2.merge([np.zeros_like(gray), gray, np.zeros_like(gray)])

def thermal_view(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    return cv2.applyColorMap(gray, cv2.COLORMAP_INFERNO)

def detect_camo(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 30, 100)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for cnt in contours:
        if cv2.contourArea(cnt) > 3000:
            cv2.drawContours(frame, [cnt], -1, (0, 165, 255), 1)
    return frame

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
    print("[INIT] Booting Project FEAT Edge Node...")
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    ret, frame1 = cap.read()
    ret, frame2 = cap.read()
    if not ret:
        print("[ERROR] Camera feed not detected. Check connections.")
        return

    prev_time = 0
    night_mode = False
    thermal_mode = False
    camo_mode = False
    target_count = 0

    print("[SYSTEM] FEAT HUD Active.")
    print("  N = Night Vision | T = Thermal | C = Camo | Q = Quit")

    while cap.isOpened():

        # --- VISION MODES ---
        display_frame = frame1.copy()

        if night_mode:
            display_frame = night_vision(display_frame)
        elif thermal_mode:
            display_frame = thermal_view(display_frame)

        if camo_mode:
            display_frame = detect_camo(display_frame)

        # --- MOTION / THREAT DETECTION ---
        diff = cv2.absdiff(frame1, frame2)
        gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        _, thresh = cv2.threshold(blur, 25, 255, cv2.THRESH_BINARY)
        dilated = cv2.dilate(thresh, None, iterations=3)
        contours, _ = cv2.findContours(dilated, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

        motion_score = 0
        target_count = 0
        status = "SECURE"
        status_color = (0, 255, 0)

        for contour in contours:
            if cv2.contourArea(contour) < 1500:
                continue
            motion_score += cv2.contourArea(contour)
            target_count += 1
            status = "THREAT DETECTED"
            status_color = (0, 0, 255)
            (x, y, w, h) = cv2.boundingRect(contour)
            cv2.rectangle(display_frame, (x, y), (x + w, y + h), (0, 0, 255), 2)
            cv2.putText(display_frame, f"TARGET LOCK #{target_count}",
                        (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

        # --- SLOW MOVEMENT DETECTION ---
        if 500 < motion_score <= 5000:
            cv2.putText(display_frame, "!! SLOW MOVEMENT DETECTED !!",
                        (10, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 165, 255), 2)

        # --- THREAT LEVEL ---
        threat_level, threat_color = get_threat_level(target_count, motion_score)

        # --- HUD ---
        height, width = display_frame.shape[:2]

        # Crosshair
        cx, cy = width // 2, height // 2
        cv2.line(display_frame, (cx - 20, cy), (cx + 20, cy), (0, 255, 0), 1)
        cv2.line(display_frame, (cx, cy - 20), (cx, cy + 20), (0, 255, 0), 1)
        cv2.circle(display_frame, (cx, cy), 10, (0, 255, 0), 1)

        # Border glow (red if threat)
        border_color = (0, 0, 255) if status == "THREAT DETECTED" else (0, 255, 0)
        cv2.rectangle(display_frame, (3, 3), (width - 3, height - 3), border_color, 3)

        # FPS
        current_time = time.time()
        fps = 1 / (current_time - prev_time) if prev_time else 0
        prev_time = current_time

        # Timestamp
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Active mode indicator
        mode_text = "NORMAL"
        if night_mode: mode_text = "NIGHT VISION"
        elif thermal_mode: mode_text = "THERMAL"
        if camo_mode: mode_text += "+CAMO"

        # HUD Text
        cv2.putText(display_frame, "FEAT OS v0.2", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        cv2.putText(display_frame, f"STATUS: {status}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, status_color, 2)
        cv2.putText(display_frame, f"THREAT: {threat_level}", (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, threat_color, 2)
        cv2.putText(display_frame, f"TARGETS: {target_count}", (10, 120) if motion_score <= 500 else (10, 150),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        cv2.putText(display_frame, f"MODE: {mode_text}", (10, height - 50), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
        cv2.putText(display_frame, f"FPS: {int(fps)}", (width - 100, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        cv2.putText(display_frame, f"TARGETS: {target_count}", (width - 130, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        cv2.putText(display_frame, timestamp, (10, height - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

        # --- DISPLAY ---
        cv2.imshow("Project FEAT - Tactical HUD", display_frame)

        frame1 = frame2
        ret, frame2 = cap.read()

        # Key controls
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

    cap.release()
    cv2.destroyAllWindows()
    print("[SYSTEM] Shutting down...")

if __name__ == "__main__":
    main()

    # At top
from core.ai_engine import AIEngine

# After cap setup
ai = AIEngine()
frame_count = 0

# Inside while loop (after motion detection)
frame_count += 1
if frame_count % 3 == 0:  # Run AI every 3 frames (saves CPU)
    ai_results = ai.detect(display_frame)
    detections = ai.get_detections(ai_results)

    for d in detections:
        x1, y1, x2, y2 = d["bbox"]
        # Draw AI box (yellow = AI detected)
        cv2.rectangle(display_frame, (x1, y1), (x2, y2), (0, 255, 255), 2)
        cv2.putText(display_frame,
                    f"{d['label']} {d['conf']:.0%} | {d['distance']}m | {d['zone']}",
                    (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)

                    # At top
from core.defense_shield import DefenseShield

# After cap setup
shield = DefenseShield()

# Inside while loop (before AI detection)
# Sanitize frame first
clean_frame = shield.sanitize(display_frame.copy())

# Check for adversarial attack
is_adv, adv_score = shield.is_adversarial(display_frame)
if is_adv:
    cv2.putText(display_frame, f"!! ADVERSARIAL PATCH DETECTED {adv_score}",
                (10, 180), cv2.FONT_HERSHEY_SIMPLEX,
                0.6, (0, 0, 255), 2)

# Camo mode (only when C is pressed)
if camo_mode:
    display_frame = shield.detect_camo(display_frame)

# Pass clean_frame to AI instead of raw frame
ai_results = ai.detect(clean_frame)