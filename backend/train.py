from ultralytics import YOLO

def train_custom_model():
    # Load a model
    model = YOLO("yolov8n.pt")  # load a pretrained model (recommended for training)

    # Train the model
    # You need a 'data.yaml' file that points to your dataset
    # Example dataset structure:
    # dataset/
    #   images/
    #     train/
    #     val/
    #   labels/
    #     train/
    #     val/
    #   data.yaml
    
    print("Starting training... (This requires a dataset in 'data.yaml')")
    results = model.train(data="data.yaml", epochs=100, imgsz=640, device='cpu') # Use device=0 for GPU
    
    print("Training complete!")
    print(f"Best model saved at: {results.save_dir}")

if __name__ == "__main__":
    # Uncomment the line below if you have a 'data.yaml' file ready
    # train_custom_model()
    print("To train, you need a labeled dataset. Check the comments in this file.")
