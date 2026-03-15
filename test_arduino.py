import serial
import time

SERIAL_PORT = 'COM5'
BAUD_RATE = 115200

print(f"Testing Arduino connection on {SERIAL_PORT} at {BAUD_RATE} baud...")

try:
    arduino = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
    print("✅ Port opened successfully!")
    print("Waiting for data...\n")
    
    # Read 20 lines of data to verify it's working
    count = 0
    while count < 20:
        if arduino.in_waiting > 0:
            line = arduino.readline().decode('utf-8').strip()
            if line:
                print(f"Data received: {line}")
                count += 1
                
    print("\n✅ Test Complete. Arduino is sending data correctly.")
    arduino.close()
    
except serial.SerialException as e:
    print(f"\n❌ Connection failed. Is the Arduino plugged in and the port correct?")
    print(f"Error details: {e}")
except Exception as e:
    print(f"\n❌ An unexpected error occurred: {e}")
