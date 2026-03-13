import cv2
import numpy as np

class DefenseShield:
    def __init__(self):
        print("[SHIELD] Defense Shield Online...")

    def feature_squeeze(self, frame):
        return (frame // 32) * 32

    def spatial_smooth(self, frame):
        return cv2.GaussianBlur(frame, (5, 5), 0)

    def median_filter(self, frame):
        return cv2.medianBlur(frame, 3)

    def detect_camo(self, frame):
        gray     = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        edges    = cv2.Canny(gray, 30, 100)
        contours, _ = cv2.findContours(
            edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        for cnt in contours:
            if cv2.contourArea(cnt) > 3000:
                cv2.drawContours(frame, [cnt], -1, (0, 165, 255), 1)
                x, y, w, h = cv2.boundingRect(cnt)
                cv2.putText(frame, "CAMO SUSPECT",
                            (x, y - 5),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.4, (0, 165, 255), 1)
        return frame

    def is_adversarial(self, frame):
        original = frame.astype(np.float32)
        squeezed = self.feature_squeeze(frame).astype(np.float32)
        diff     = np.mean(np.abs(original - squeezed))
        return diff > 15, round(diff, 2)

    def sanitize(self, frame):
        frame = self.feature_squeeze(frame)
        frame = self.spatial_smooth(frame)
        frame = self.median_filter(frame)
        return frame