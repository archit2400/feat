import cv2
import numpy as np
import datetime

class HUDEngine:
    def __init__(self):
        print("[HUD] HUD Engine Online...")
        self.flash_counter = 0

    def night_vision(self, frame):
        gray     = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        clahe    = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        return cv2.merge([
            np.zeros_like(enhanced),
            enhanced,
            np.zeros_like(enhanced)
        ])

    def thermal_view(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        return cv2.applyColorMap(gray, cv2.COLORMAP_INFERNO)

    def draw_crosshair(self, frame):
        h, w   = frame.shape[:2]
        cx, cy = w // 2, h // 2
        cv2.line(frame,   (cx - 20, cy), (cx + 20, cy), (0, 255, 0), 1)
        cv2.line(frame,   (cx, cy - 20), (cx, cy + 20), (0, 255, 0), 1)
        cv2.circle(frame, (cx, cy), 10, (0, 255, 0), 1)
        cv2.circle(frame, (cx, cy), 30, (0, 255, 0), 1)
        return frame

    def draw_border(self, frame, threat_level):
        h, w = frame.shape[:2]
        self.flash_counter += 1
        if threat_level == "CRITICAL":
            color = (0, 0, 255) if self.flash_counter % 10 < 5 else (0, 100, 255)
        elif threat_level == "HIGH":
            color = (0, 100, 255)
        elif threat_level == "MEDIUM":
            color = (0, 165, 255)
        else:
            color = (0, 255, 0)
        cv2.rectangle(frame, (3, 3), (w - 3, h - 3), color, 3)
        return frame

    def draw_zone_map(self, frame, detections):
        h, w           = frame.shape[:2]
        map_x, map_y   = w - 110, h - 80
        # Background
        cv2.rectangle(frame,
                      (map_x, map_y),
                      (map_x + 100, map_y + 70),
                      (0, 40, 0), -1)
        cv2.rectangle(frame,
                      (map_x, map_y),
                      (map_x + 100, map_y + 70),
                      (0, 255, 0), 1)
        cv2.putText(frame, "ZONE MAP",
                    (map_x + 10, map_y + 12),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.3, (0, 255, 0), 1)
        # Zone dividers
        cv2.line(frame,
                 (map_x + 33, map_y),
                 (map_x + 33, map_y + 70), (0, 100, 0), 1)
        cv2.line(frame,
                 (map_x + 66, map_y),
                 (map_x + 66, map_y + 70), (0, 100, 0), 1)
        # Plot targets
        for d in detections:
            if d["zone"]   == "LEFT FLANK": dot_x = map_x + 16
            elif d["zone"] == "CENTER":     dot_x = map_x + 50
            else:                           dot_x = map_x + 83
            cv2.circle(frame, (dot_x, map_y + 40), 5, (0, 0, 255), -1)
        return frame

    def draw_detections(self, frame, detections):
        for i, d in enumerate(detections):
            x1, y1, x2, y2 = d["bbox"]
            conf  = d["conf"]
            label = d["label"]
            dist  = d["distance"]
            zone  = d["zone"]

            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 255), 2)

            text = f"{label} {conf:.0%} | {dist}m"
            (tw, th), _ = cv2.getTextSize(
                text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1
            )
            cv2.rectangle(frame,
                          (x1, y1 - 20), (x1 + tw, y1),
                          (0, 255, 255), -1)
            cv2.putText(frame, text, (x1, y1 - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
            cv2.putText(frame, zone, (x1, y2 + 15),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1)
            cv2.putText(frame, f"T{i+1}", (x1 - 20, y1 + 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
        return frame

    def render(self, frame, status, threat_level,
               threat_color, target_count, fps,
               mode_text, detections, adv_detected=False,
               iq_analysis=None):

        h, w      = frame.shape[:2]
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        frame = self.draw_border(frame, threat_level)
        frame = self.draw_crosshair(frame)
        frame = self.draw_zone_map(frame, detections)
        frame = self.draw_detections(frame, detections)

        # Top left
        cv2.putText(frame, "FEAT OS v0.2",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        cv2.putText(frame, f"STATUS: {status}",
                    (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                    (0, 0, 255) if status == "THREAT DETECTED" else (0, 255, 0), 2)
        cv2.putText(frame, f"THREAT: {threat_level}",
                    (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, threat_color, 2)
        cv2.putText(frame, f"TARGETS: {target_count}",
                    (10, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        # Adversarial warning
        if adv_detected:
            cv2.putText(frame, "!! PATCH ATTACK !!",
                        (10, 150),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

        # IQ AI analysis on HUD
        if iq_analysis:
            cv2.putText(frame, f"IQ: {iq_analysis[:40]}",
                        (10, 180),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 200, 255), 1)

        # Top right
        cv2.putText(frame, f"FPS: {int(fps)}",
                    (w - 110, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        cv2.putText(frame, f"TARGETS: {target_count}",
                    (w - 130, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        # Bottom
        cv2.putText(frame, f"MODE: {mode_text}",
                    (10, h - 50), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
        cv2.putText(frame, timestamp,
                    (10, h - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

        return frame