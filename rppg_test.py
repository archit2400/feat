import cv2
import numpy as np
import time
from collections import deque
from scipy.signal import butter, filtfilt

# --- Configuration ---
BUFFER_SIZE = 150 # Stores ~5 seconds of frames at 30fps
FPS_ASSUMPTION = 30.0 
MIN_BPM = 50.0
MAX_BPM = 180.0

# Initialize the Haar Cascade for fast, lightweight face detection
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

# Data buffers
times = deque(maxlen=BUFFER_SIZE)
green_signal = deque(maxlen=BUFFER_SIZE)

CAMERA_INDEX = 1  # <-- Change this to 0, 1, or 2 to select your Brio 101
# Initialize webcam (Added CAP_DSHOW for better Windows compatible external cam loading)
cap = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_DSHOW)

# --- Bandpass Filter Setup ---
# This filters out noise (like camera flicker) and only keeps frequencies that match human heart rates
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

current_bpm = 0

print("SYSTEM ONLINE: Initiating Biometric Scan...")

while True:
    ret, frame = cap.read()
    if not ret: break

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.3, 5)

    if len(faces) > 0:
        # Grab the first detected face
        (x, y, w, h) = faces[0]
        
        # 1. Isolate the Forehead (Best spot for rPPG)
        fh_x = int(x + (w * 0.25))
        fh_y = int(y + (h * 0.05))
        fh_w = int(w * 0.5)
        fh_h = int(h * 0.15)
        
        # Draw target lock on face and forehead
        cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 0, 255), 2)
        cv2.rectangle(frame, (fh_x, fh_y), (fh_x+fh_w, fh_y+fh_h), (0, 255, 0), 2)
        cv2.putText(frame, "TARGET LOCKED", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

        # 2. Extract the Green Channel from the Forehead ROI
        forehead_roi = frame[fh_y:fh_y+fh_h, fh_x:fh_x+fh_w]
        # BGR format, so index 1 is Green
        green_channel = forehead_roi[:, :, 1] 
        
        # Calculate the average green value and store it
        mean_green = np.mean(green_channel)
        green_signal.append(mean_green)
        times.append(time.time())

        # 3. Process the Signal (When we have enough data)
        if len(green_signal) == BUFFER_SIZE:
            # Calculate actual FPS based on our buffer to ensure accurate math
            time_diff = times[-1] - times[0]
            actual_fps = BUFFER_SIZE / time_diff
            
            # Detrend the signal (remove the DC offset)
            detrended_signal = np.diff(green_signal)
            
            # Apply our bandpass filter to isolate human heartbeat frequencies
            try:
                filtered_signal = apply_filter(detrended_signal, actual_fps)
                
                # Fast Fourier Transform (FFT) to find the dominant frequency
                fft_data = np.abs(np.fft.rfft(filtered_signal))
                fft_freqs = np.fft.rfftfreq(len(filtered_signal), 1.0/actual_fps)
                
                # Find the highest peak in the valid human heart rate range
                valid_indices = np.where((fft_freqs >= MIN_BPM/60.0) & (fft_freqs <= MAX_BPM/60.0))
                if len(valid_indices[0]) > 0:
                    valid_fft = fft_data[valid_indices]
                    valid_freqs = fft_freqs[valid_indices]
                    
                    peak_idx = np.argmax(valid_fft)
                    dominant_freq = valid_freqs[peak_idx]
                    
                    # Convert Frequency (Hz) to BPM
                    current_bpm = int(dominant_freq * 60.0)
            except Exception as e:
                pass # Bypass filter errors during initialization jitter

    # --- HUD OVERLAY ---
    # Display the calculating BPM
    if len(green_signal) < BUFFER_SIZE:
        status_text = f"CALIBRATING... {int((len(green_signal)/BUFFER_SIZE)*100)}%"
        color = (0, 255, 255) # Yellow
    else:
        status_text = f"BIO-SCAN: {current_bpm} BPM"
        color = (0, 255, 0) # Green

    cv2.putText(frame, status_text, (30, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
    cv2.putText(frame, "FEAT: TACTICAL VISION OPTICS", (30, frame.shape[0] - 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)

    cv2.imshow('Project FEAT - Biometric Scanner', frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
