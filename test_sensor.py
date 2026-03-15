import serial
import time

SERIAL_PORT = 'COM5'
BAUD_RATE = 115200

try:
    print(f"Connecting to Arduino on {SERIAL_PORT}...")
    arduino = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
    time.sleep(2)
    print("Connected! Waiting for pulse data...\n")
    
    while True:
        if arduino.in_waiting > 0:
            raw_line = arduino.readline()
            try:
                # Try to decode it as standard text
                clean_text = raw_line.decode('utf-8').strip()
                print(f"I see: '{clean_text}'")
            except Exception as e:
                # If it's garbled, show the raw bytes
                print(f"Garbled Bytes Received: {raw_line}")
                
except Exception as e:
    print(f"Failed to connect: {e}")
