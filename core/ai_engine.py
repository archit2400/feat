from ultralytics import YOLO

class AIEngine:
    def __init__(self):
        print("[AI] Loading YOLOv8 model...")
        self.model = YOLO("models/yolov8n.pt")
        self.names = self.model.names
        self.distance_history = {} # Store recent distances for smoothing
        print("[AI] Model ready!")

    def detect(self, frame):
        results = self.model(
            frame,
            imgsz=320,
            conf=0.45,        # Slightly lower confidence to catch smaller objects
            # classes=[0],    # REMOVED: Now we detect all objects, not just people
            verbose=False
        )
        return results[0]

    def get_detections(self, results):
        detections = []
        for box in results.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            conf  = float(box.conf[0])
            label = self.names[int(box.cls[0])]

            # Zone detection
            cx = x1 + (x2 - x1) // 2
            if cx < 213:        zone = "LEFT FLANK"
            elif cx < 426:      zone = "CENTER"
            else:               zone = "RIGHT FLANK"

            # Distance estimation & Smoothing (Rolling Average)
            h    = y2 - y1
            # Assuming average human height is ~1.7 meters (170cm)
            # Standard webcam focal length ~ 600 pixels
            # Distance (meters) = (Real Height (m) * Focal Length (px)) / Image Height (px)
            raw_dist = round((1.7 * 600) / h, 1) if h > 0 else 0
            
            # Use object label as a generic ID to smooth distance over time
            if label not in self.distance_history:
                self.distance_history[label] = [raw_dist]
            else:
                self.distance_history[label].append(raw_dist)
                if len(self.distance_history[label]) > 5: # Average over last 5 readings
                    self.distance_history[label].pop(0)
            
            smooth_dist = round(sum(self.distance_history[label]) / len(self.distance_history[label]), 1)

            # THREAT ASSESSMENT LOGIC (Object + Proximity)
            # Define objects that are considered inherent threats
            weapon_classes = ["knife", "scissors", "baseball bat", "gun", "cell phone"] # Added cell phone for easy testing
            
            is_threat = False
            display_label = label.upper()

            if label in weapon_classes:
                is_threat = True
                display_label = f"THREAT ({label.upper()})"
            elif label == "person":
                if smooth_dist < 3.0 and smooth_dist > 0.0:
                    is_threat = True
                    display_label = "THREAT (PROXIMITY BREACH)"
                else:
                    display_label = "PERSON (BYSTANDER)"
            else:
                display_label = f"OBJ: {label.upper()}" # Generic object

            detections.append({
                "label"     : display_label,
                "is_threat" : is_threat,
                "conf"      : conf,
                "bbox"      : (x1, y1, x2, y2),
                "distance"  : smooth_dist,
                "zone"      : zone,
                "raw_label" : label
            })
        return detections