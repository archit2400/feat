from ultralytics import YOLO

def main():
    print("Loading original YOLOv8 Nano model...")
    model = YOLO("models/yolov8n.pt")
    
    # Export the model to TFLite format with 8-bit Quantization!
    # TFLite is highly optimized for ARM CPUs (like the Raspberry Pi).
    print("Compressing and Quantizing to TFLite INT8 format...")
    model.export(format="tflite", int8=True)
    
    print("Quantization Complete! Ready for the Edge.")

if __name__ == "__main__":
    main()
