from ultralytics import YOLO

class AIEngine:
    def __init__(self):
        print("[AI] Loading YOLOv8 model...")
        self.model = YOLO("models/yolov8n.pt")
        self.names = self.model.names
        print("[AI] Model ready!")

    def detect(self, frame):
        results = self.model(
            frame,
            imgsz=320,
            conf=0.5,
            classes=[0],      # person only
            verbose=False
        )
        return results[0]

    def get_detections(self, results):
        detections = []
        for box in results.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            conf  = float(box.conf[0])
            label = self.names[int(box.cls[0])]

            # Distance estimation
            h    = y2 - y1
            dist = round((170 * 500) / h, 1) if h > 0 else 0

            # Zone detection
            cx = x1 + (x2 - x1) // 2
            if cx < 213:        zone = "LEFT FLANK"
            elif cx < 426:      zone = "CENTER"
            else:               zone = "RIGHT FLANK"

            detections.append({
                "label"   : label,
                "conf"    : conf,
                "bbox"    : (x1, y1, x2, y2),
                "distance": dist,
                "zone"    : zone
            })
        return detections