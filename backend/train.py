from ultralytics import YOLO

if __name__ == '__main__':
    # Load a model
    # Load a model
    model = YOLO("yolov8m.pt")  # load a pretrained model (recommended for training)

    # Train the model
    # Using absolute path to data.yaml to avoid confusion
    print("Starting training...")
    # Increased epochs for better accuracy
    results = model.train(data="dataset/data.yaml", epochs=50, imgsz=640)
    print("Training complete!")
