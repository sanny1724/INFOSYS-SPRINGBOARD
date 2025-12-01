import cv2
from ultralytics import YOLO
import os

# Load model globally to avoid reloading (or load inside if memory is concern)
# Using 'yolov8n.pt' for speed. It will auto-download.
model = YOLO('yolov8n.pt') 

import json

def process_video(video_path: str):
    print(f"Starting processing for {video_path}")
    
    filename = os.path.basename(video_path)
    is_image = filename.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.webp'))
    print(f"Filename: {filename}, Is Image: {is_image}", flush=True)
    
    output_path = video_path.replace(filename, f"processed_{filename}")
    json_path = output_path.replace(os.path.splitext(output_path)[1], '.json')
    
    poacher_detected = False
    weapon_detected = False
    max_poacher_conf = 0.0
    max_weapon_conf = 0.0
    
    # Custom classes
    # Added 63 (laptop), 73 (book), and 74 (clock) because the model misclassifies weapons.
    # weapon_classes moved to global
    # animal_classes moved to global

    try:
        if is_image:
            frame = cv2.imread(video_path)
            if frame is None:
                print("Error opening image file")
                with open(json_path, "w") as f:
                    json.dump({"status": "error", "message": "Could not open image file"}, f)
                return
            
            # Ultra-low confidence to catch everything
            # Custom plotting to label weapons clearly
            annotated_frame = frame.copy()
            
            results = model(frame, conf=0.05)
            
            detections = []
            for box in results[0].boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                cls = int(box.cls[0])
                conf = float(box.conf[0])
                
                # Default values
                label = model.names[cls]
                color = (0, 255, 0)
                class_id = -1 # Unknown
                
                if cls == 0: # Person
                    class_id = 0
                    label = "person" # User requested 'person' class name
                    display_label = f"Poacher {int(conf * 100)}%" # Keep visual alert
                    color = (0, 0, 255) # Red for poacher
                    poacher_detected = True
                    max_poacher_conf = max(max_poacher_conf, conf)
                    
                elif cls in weapon_classes:
                    class_id = 2
                    label = "weapon" # User requested strict 'weapon' label
                    display_label = f"weapon {int(conf * 100)}%"
                    color = (0, 0, 255) # Red for weapon
                    weapon_detected = True
                    max_weapon_conf = max(max_weapon_conf, conf)
                    
                elif cls in animal_classes:
                    class_id = 1
                    label = "animal"
                    display_label = f"animal {int(conf * 100)}%"
                    color = (255, 255, 0) # Cyan/Yellow for animal
                else:
                    display_label = f"{label} {int(conf * 100)}%"
    
                # Add to detailed detections list
                if class_id != -1:
                    detections.append({
                        "box": [x1, y1, x2, y2],
                        "class_id": class_id,
                        "label": label,
                        "confidence": conf
                    })
                
                # Draw box
                cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, 2)
                # Draw label
                cv2.putText(annotated_frame, display_label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2)
            
            # Analyze detections
            with open("debug_log.txt", "a") as log:
                log.write(f"Filename: {filename}, Is Image: {is_image}\n")
                log.write(f"Detections found: {len(results[0].boxes)}\n")
                for det in detections:
                    log.write(f"Detected: {det['label']} (Class {det['class_id']}) - Confidence: {det['confidence']:.2f}\n")
                    
            cv2.imwrite(output_path, annotated_frame)
            
        else:
            # Video Processing
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                print("Error opening video file")
                with open(json_path, "w") as f:
                    json.dump({"status": "error", "message": "Could not open video file"}, f)
                return
    
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = int(cap.get(cv2.CAP_PROP_FPS))
            
            fourcc = cv2.VideoWriter_fourcc(*'mp4v') 
            out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
            
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break
                
                results = model(frame, conf=0.15)
                annotated_frame = results[0].plot()
                
                for box in results[0].boxes:
                    cls = int(box.cls[0])
                    conf = float(box.conf[0])
                    
                    if cls == 0:
                        poacher_detected = True
                        max_poacher_conf = max(max_poacher_conf, conf)
                    if cls in weapon_classes:
                        weapon_detected = True
                        max_weapon_conf = max(max_weapon_conf, conf)
                    
                out.write(annotated_frame)
    
            cap.release()
            out.release()
        
        mail_sent = False
        if poacher_detected:
            print("ALERT: Poacher (Person) detected!")
            from mailer import send_alert_email
            mail_sent = send_alert_email(output_path)
    
        # Save results to JSON
        results_data = {
            "status": "completed",
            "poacher_detected": poacher_detected,
            "weapon_detected": "Yes" if weapon_detected else "No",
            "poacher_confidence": round(max_poacher_conf * 100, 1),
            "weapon_confidence": round(max_weapon_conf * 100, 1),
            "mail_sent": "Yes" if mail_sent else "No (Check .env)" if poacher_detected else "N/A",
            "video_url": f"http://localhost:8000/uploads/{os.path.basename(output_path)}",
            "detections": detections if is_image else [] # Only detailed detections for images for now
        }
        
        with open(json_path, "w") as f:
            json.dump(results_data, f)
    
        print(f"Finished processing. Saved to {output_path}")

    except Exception as e:
        print(f"Error processing video: {e}")
        with open(json_path, "w") as f:
            json.dump({"status": "error", "message": str(e)}, f)


import time
from mailer import send_alert_email
import cv2
import numpy as np
import base64

# Global variable for rate limiting
last_email_time = 0
EMAIL_COOLDOWN = 60 # Seconds

# Global classes
animal_classes = [14, 15, 16, 17, 18, 19, 20, 21, 22, 23] # Bird, Cat, Dog, Horse, Sheep, Cow, Elephant, Bear, Zebra, Giraffe
weapon_classes = [43, 34, 76, 25, 66, 67, 63, 73, 74, 39, 41, 40, 42] # Combined list

def process_frame(image_bytes):
    global last_email_time
    
    # Decode image
    nparr = np.frombuffer(image_bytes, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    if frame is None:
        return {"error": "Could not decode image"}

    # Run detection
    results = model(frame, conf=0.05) # Low conf
    
    detections = []
    poacher_detected = False
    weapon_detected = False
    max_poacher_conf = 0.0
    max_weapon_conf = 0.0
    
    # Use global weapon classes
    # weapon_classes defined at top of file (need to move it to global scope first)
    
    for box in results[0].boxes:
        x1, y1, x2, y2 = map(int, box.xyxy[0])
        cls = int(box.cls[0])
        conf = float(box.conf[0])
        
        # Default values
        label = model.names[cls]
        color = (0, 255, 0) # Green
        class_id = -1 
        
        if cls == 0: # Person
            class_id = 0
            label = "person"
            color = (0, 0, 255) # Red
            poacher_detected = True
            max_poacher_conf = max(max_poacher_conf, conf)
            
        elif cls in weapon_classes:
            class_id = 2
            label = model.names[cls]
            color = (0, 0, 255) # Red
            weapon_detected = True
            max_weapon_conf = max(max_weapon_conf, conf)
            
        elif cls in animal_classes:
            class_id = 1
            label = "animal"
            color = (255, 255, 0) # Cyan
        
        # Draw on frame
        if class_id != -1:
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(frame, f"{label} {int(conf*100)}%", (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

            detections.append({
                "box": [x1, y1, x2, y2],
                "class_id": class_id,
                "label": label,
                "confidence": conf
            })

    # Email Alert Logic (Rate Limited)
    mail_sent = False
    current_time = time.time()
    if (poacher_detected or weapon_detected) and (current_time - last_email_time > EMAIL_COOLDOWN):
        temp_path = "temp_alert_frame.jpg"
        cv2.imwrite(temp_path, frame)
        subject = "EcoEye Alert: Poacher/Weapon Detected (Live)"
        body = f"Alert! Detection in live feed.\nPoacher: {poacher_detected}\nWeapon: {weapon_detected}"
        # Fix argument order: image_path, subject, body
        send_alert_email(temp_path, subject, body)
        last_email_time = current_time
        mail_sent = True

    # Encode frame to base64
    _, buffer = cv2.imencode('.jpg', frame)
    jpg_as_text = base64.b64encode(buffer).decode('utf-8')

    return {
        "status": "completed",
        "image": f"data:image/jpeg;base64,{jpg_as_text}",
        "detections": detections,
        "summary": {
            "poacher": { "detected": poacher_detected, "confidence": max_poacher_conf },
            "weapon": { "detected": weapon_detected, "confidence": max_weapon_conf },
            "mail": { "detected": mail_sent, "confidence": 1.0 if mail_sent else 0.0 }
        }
    }
