import cv2
import time
import numpy as np
from flask import Flask, Response, render_template_string
from core.ai_engine import AIEngine
from core.defense_shield import DefenseShield
from core.hud_engine import HUDEngine
from core.iq_agent import IQAgent

app    = Flask(__name__)
ai     = AIEngine()
shield = DefenseShield()
hud    = HUDEngine()
iq     = IQAgent()

def get_threat_level(num_targets, motion_score):
    score = num_targets * 20
    if motion_score > 5000:   score += 40
    elif motion_score > 500:  score += 20
    if score >= 80:   return "CRITICAL", (0, 0, 255)
    elif score >= 50: return "HIGH",     (0, 100, 255)
    elif score >= 20: return "MEDIUM",   (0, 165, 255)
    else:             return "LOW",      (0, 255, 0)

def generate_frames():
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    ret, frame1 = cap.read()
    ret, frame2 = cap.read()

    if not ret:
        print("[ERROR] Camera not found.")
        return

    prev_time    = 0
    frame_count  = 0
    detections   = []
    iq_analysis  = None

    print("[SYSTEM] Stream started...")

    while cap.isOpened():
        display_frame = frame1.copy()

        # Defense shield
        clean_frame  = shield.sanitize(display_frame.copy())
        is_adv, _    = shield.is_adversarial(display_frame)

        # Motion detection
        diff        = cv2.absdiff(frame1, frame2)
        gray        = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
        blur        = cv2.GaussianBlur(gray, (5, 5), 0)
        _, thresh   = cv2.threshold(blur, 25, 255, cv2.THRESH_BINARY)
        dilated     = cv2.dilate(thresh, None, iterations=3)
        contours, _ = cv2.findContours(
            dilated, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE
        )

        motion_score = 0
        status       = "SECURE"

        for contour in contours:
            if cv2.contourArea(contour) < 1500:
                continue
            motion_score += cv2.contourArea(contour)
            status = "THREAT DETECTED"

        # AI detection every 3 frames
        frame_count += 1
        if frame_count % 3 == 0:
            ai_results = ai.detect(clean_frame)
            detections = ai.get_detections(ai_results)

        # IQ AI every 30 frames
        if frame_count % 30 == 0 and len(detections) > 0:
            threat_level, _ = get_threat_level(len(detections), motion_score)
            iq_analysis     = iq.analyze(detections, threat_level, motion_score)
            if iq_analysis:
                print(f"[IQ AI] {iq_analysis}")

        # Threat level
        threat_level, threat_color = get_threat_level(
            len(detections), motion_score
        )

        # FPS
        current_time = time.time()
        fps          = 1 / (current_time - prev_time) if prev_time else 0
        prev_time    = current_time

        # Render HUD
        display_frame = hud.render(
            frame        = display_frame,
            status       = status,
            threat_level = threat_level,
            threat_color = threat_color,
            target_count = len(detections),
            fps          = fps,
            mode_text    = "NORMAL",
            detections   = detections,
            adv_detected = is_adv,
            iq_analysis  = iq_analysis
        )

        # Encode and stream
        ret, buffer    = cv2.imencode('.jpg', display_frame)
        frame_bytes    = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n'
               + frame_bytes + b'\r\n')

        frame1 = frame2
        ret, frame2 = cap.read()

    cap.release()


@app.route('/')
def index():
    return render_template_string('''
    <html>
    <head>
        <title>Project FEAT - Tactical HUD</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                background-color: #0a0a0a;
                color: #00ff00;
                font-family: monospace;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                min-height: 100vh;
            }
            h1 {
                text-shadow: 0 0 10px #00ff00;
                font-size: 24px;
                margin-bottom: 20px;
                letter-spacing: 4px;
            }
            img {
                border: 2px solid #00ff00;
                border-radius: 4px;
                box-shadow: 0 0 30px #00ff00;
            }
            .status {
                margin-top: 15px;
                font-size: 12px;
                color: #00aa00;
                letter-spacing: 2px;
            }
        </style>
    </head>
    <body>
        <h1>⚔ PROJECT FEAT — LIVE UPLINK</h1>
        <img src="/video_feed" width="640" height="480"/>
        <div class="status">
            FEAT OS v0.2 &nbsp;|&nbsp;
            EDGE NODE ACTIVE &nbsp;|&nbsp;
            STREAM LIVE &nbsp;|&nbsp;
            DEFENSE SHIELD ON
        </div>
    </body>
    </html>
    ''')


@app.route('/video_feed')
def video_feed():
    return Response(
        generate_frames(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )


if __name__ == "__main__":
    print("[SYSTEM] Starting FEAT Web Server...")
    print("[SYSTEM] Open browser → http://<YOUR_PI_IP>:5000")
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)