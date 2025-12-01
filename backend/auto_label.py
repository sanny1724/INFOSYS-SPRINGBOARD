from ultralytics import YOLO
import os
import cv2

def auto_label_images(source_dir, output_dir):
    # Load the model (using the medium model for better accuracy)
    model = YOLO('yolov8m.pt')
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Supported image extensions
    valid_extensions = ('.jpg', '.jpeg', '.png', '.bmp', '.webp')
    
    files = [f for f in os.listdir(source_dir) if f.lower().endswith(valid_extensions)]
    print(f"Found {len(files)} images to label...")
    
    for filename in files:
        file_path = os.path.join(source_dir, filename)
        
        # Run detection
        results = model(file_path, conf=0.25) # Confidence threshold
        
        # Prepare label file path
        label_filename = os.path.splitext(filename)[0] + ".txt"
        label_path = os.path.join(output_dir, label_filename)
        
        with open(label_path, "w") as f:
            for result in results:
                for box in result.boxes:
                    # Get class ID
                    cls = int(box.cls[0])
                    
                    # Only label classes we care about if needed, or label all
                    # YOLO format: <class> <x_center> <y_center> <width> <height>
                    # Coordinates are normalized (0-1)
                    
                    x, y, w, h = box.xywhn[0]
                    
                    f.write(f"{cls} {x:.6f} {y:.6f} {w:.6f} {h:.6f}\n")
        
        print(f"Labeled: {filename}")

if __name__ == "__main__":
    # INSTRUCTIONS:
    # 1. Put your raw images in a folder (e.g., 'raw_images')
    # 2. Update the paths below
    # 3. Run this script
    
    source_images = "raw_images" # Change this to your image folder
    output_labels = "auto_labels" # Where to save the .txt files
    
    if not os.path.exists(source_images):
        print(f"Error: Source directory '{source_images}' not found.")
        print("Please create a folder named 'raw_images' and put your images there.")
    else:
        auto_label_images(source_images, output_labels)
