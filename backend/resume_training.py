from ultralytics import YOLO

if __name__ == '__main__':
    # Load the last checkpoint
    model = YOLO("runs/detect/train3/weights/last.pt")

    # Resume training
    print("Resuming training from runs/detect/train3/weights/last.pt...")
    results = model.train(resume=True)
    print("Training complete!")
