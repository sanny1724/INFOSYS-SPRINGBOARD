import cv2
from ultralytics import YOLO
import os
import json
import time
from mailer import send_alert_email
import numpy as np
import base64
from datetime import datetime
import random

# Load the TRAINED model
# Dynamically find the latest run
import glob

# Base runs directory
runs_dir = os.path.join(os.path.dirname(__file__), "runs", "detect")
# Find all train folders
train_dirs = glob.glob(os.path.join(runs_dir, "train*"))
# Sort by modification time (newest last)
train_dirs.sort(key=os.path.getmtime)

if train_dirs:
    latest_run = train_dirs[-1]
    # Use last.pt because best.pt might not have updated if validation didn't improve, but last.pt has the latest epoch
    model_path = os.path.join(latest_run, "weights", "last.pt")
    print(f"Loading LATEST model from: {model_path}")
else:
    # Fallback
    model_path = r"C:\Users\sravs\.gemini\antigravity\scratch\wildeye_ai\backend\runs\detect\train2\weights\best.pt"
    print(f"No new runs found. Loading default: {model_path}")

model = YOLO(model_path)

# Global variable for rate limiting
last_email_time = 0
EMAIL_COOLDOWN = 60 # Seconds

# Custom Model Classes (from data.yaml)
# 0: poacher
# 1: ranger
# 2: weapon
# 3: ww

def process_video(video_path: str, user_email: str):
    print(f"DEBUG: process_video STARTED for {video_path}", flush=True)
    
    # Ensure absolute path
    video_path = os.path.abspath(video_path)
    
    filename = os.path.basename(video_path)
    is_image = filename.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.webp'))
    print(f"DEBUG: Filename: {filename}, Is Image: {is_image}", flush=True)
    
    output_path = video_path.replace(filename, f"processed_{filename}")
    json_path = output_path.replace(os.path.splitext(output_path)[1], '.json')
    
    print(f"DEBUG: JSON path: {json_path}", flush=True)
    print(f"DEBUG: Output path: {output_path}", flush=True)
    
    poacher_detected = False
    weapon_detected = False
    max_poacher_conf = 0.0
    max_weapon_conf = 0.0
    
    try:
        if is_image:
            # Image Processing
            # Check if file exists
            if not os.path.exists(video_path):
                print(f"ERROR: Image file not found at {video_path}", flush=True)
                raise FileNotFoundError(f"Image file not found at {video_path}")

            # Read image using cv2
            # Force absolute path for cv2
            abs_video_path = os.path.abspath(video_path)
            print(f"DEBUG: Reading image from absolute path: {abs_video_path}", flush=True)
            frame = cv2.imread(abs_video_path)
            
            if frame is None:
                print(f"ERROR: Could not read image at {video_path}. cv2.imread returned None.", flush=True)
                # Try reading with numpy if cv2 fails
                try:
                    with open(video_path, "rb") as f:
                        file_bytes = np.asarray(bytearray(f.read()), dtype=np.uint8)
                        frame = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
                except Exception as e:
                    print(f"ERROR: Fallback image read failed: {e}", flush=True)
            
            if frame is None:
                raise Exception(f"Could not open image file (invalid format or path). Path: {video_path}")
            
            annotated_frame = frame.copy()
            
            # Run with reasonable confidence
            results = model(frame, conf=0.15)
            
            detections = []
            
            # Log to file for debugging
            with open("debug_output.txt", "a", encoding="utf-8") as f:
                f.write(f"\n--- Processing {filename} ---\n")
            
            for box in results[0].boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                cls = int(box.cls[0])
                conf = float(box.conf[0])
                
                # Default values
                label = model.names[cls]
                color = (255, 255, 255) # White
                class_id = cls
                
                # Log every single detection
                with open("debug_output.txt", "a", encoding="utf-8") as f:
                    f.write(f"Found {label} (Class {cls}) - Conf: {conf}\n")
                
                valid_detection = False

                if cls == 0 and conf > 0.15: # Poacher (Lowered threshold)
                    label = "Poacher"
                    color = (0, 0, 255) # Red
                    poacher_detected = True
                    max_poacher_conf = max(max_poacher_conf, conf)
                    valid_detection = True
                    
                elif cls == 1 and conf > 0.35: # Ranger
                    label = "Ranger"
                    color = (0, 255, 0) # Green
                    valid_detection = True
                    
                elif cls == 2 and conf > 0.15: # Weapon
                    label = "Weapon"
                    color = (0, 0, 255) # Red
                    weapon_detected = True
                    max_weapon_conf = max(max_weapon_conf, conf)
                    valid_detection = True

                elif cls == 3 and conf > 0.15: # WW (Treating as suspicious/weapon)
                    label = "WW"
                    color = (0, 165, 255) # Orange
                    weapon_detected = True # Trigger alert for WW too
                    max_weapon_conf = max(max_weapon_conf, conf)
                    valid_detection = True
                
                if valid_detection:
                    display_label = f"{label} {int(conf * 100)}%"
        
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
                
                results = model(frame, conf=0.25)
                annotated_frame = results[0].plot() # Use default plot for video for speed
                
                for box in results[0].boxes:
                    cls = int(box.cls[0])
                    conf = float(box.conf[0])
                    
                    if cls == 0: # Poacher
                        poacher_detected = True
                        max_poacher_conf = max(max_poacher_conf, conf)
                    if cls == 2 or cls == 3: # Weapon
                        weapon_detected = True
                        max_weapon_conf = max(max_weapon_conf, conf)
                    
                out.write(annotated_frame)
    
            cap.release()
            out.release()
        
        mail_sent = False
        if poacher_detected or weapon_detected:
            print(f"ALERT: Threat detected! Poacher: {poacher_detected}, Weapon: {weapon_detected}")
            
            # Get Real Location (IP-based)
            try:
                import requests
                # Short timeout to not block processing
                response = requests.get("https://ipinfo.io/json", timeout=2)
                data = response.json()
                loc = data.get("loc", "").split(",")
                if len(loc) == 2:
                    lat, lng = loc[0], loc[1]
                else:
                    raise Exception("Invalid location data")
            except Exception as e:
                print(f"Warning: Could not get real location ({e}). Using default.")
                lat, lng = "17.3850", "78.4867" # Default to Hyderabad (or user's approximate area)
            
            maps_link = f"https://www.google.com/maps/search/?api=1&query={lat},{lng}"
            
            # Prioritize logged-in user's email
            recipient = user_email
            
            # Simple validation
            if "@" not in recipient:
                print(f"Warning: User '{recipient}' does not look like an email. Falling back to MAIL_RECIPIENT.")
                recipient = os.getenv("MAIL_RECIPIENT")
            
            if recipient:
                print(f"Sending email to {recipient} with location: {maps_link}")
                mail_sent = send_alert_email(output_path, recipient, location_link=maps_link)
            else:
                print("Error: No valid recipient email found.")
    
        # Save results to JSON
        results_data = {
            "status": "completed",
            "poacher_detected": poacher_detected,
            "weapon_detected": "Yes" if weapon_detected else "No",
            "poacher_confidence": round(max_poacher_conf * 100, 1),
            "weapon_confidence": round(max_weapon_conf * 100, 1),
            "mail_sent": "Yes" if mail_sent else "No (Check .env)" if (poacher_detected or weapon_detected) else "N/A",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "video_url": f"/uploads/{os.path.basename(output_path)}",
            "detections": detections if is_image else [] 
        }
        
        with open(json_path, "w") as f:
            json.dump(results_data, f)
    
        print(f"Finished processing. Saved to {output_path}")

    except Exception as e:
        print(f"Error processing video: {e}")
        with open(json_path, "w") as f:
            json.dump({"status": "error", "message": str(e)}, f)


def process_frame(image_bytes, user_email: str):
    global last_email_time
    
    # Decode image
    nparr = np.frombuffer(image_bytes, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    if frame is None:
        return {"error": "Could not decode image"}

    # Run detection
    results = model(frame, conf=0.15) # Lowered conf for better detection
    
    detections = []
    poacher_detected = False
    weapon_detected = False
    max_poacher_conf = 0.0
    max_weapon_conf = 0.0
    
    for box in results[0].boxes:
        x1, y1, x2, y2 = map(int, box.xyxy[0])
        cls = int(box.cls[0])
        conf = float(box.conf[0])
        
        # Default values
        label = model.names[cls]
        color = (255, 255, 255) 
        class_id = cls
        
        if cls == 0: # Poacher
            label = "Poacher"
            color = (0, 0, 255) # Red
            poacher_detected = True
            max_poacher_conf = max(max_poacher_conf, conf)
            
        elif cls == 1: # Ranger
            label = "Ranger"
            color = (0, 255, 0) # Green
            
        elif cls == 2: # Weapon
            label = "Weapon"
            color = (0, 0, 255) # Red
            weapon_detected = True
            max_weapon_conf = max(max_weapon_conf, conf)

        elif cls == 3: # WW
            label = "WW"
            color = (0, 165, 255) # Orange
            weapon_detected = True
            max_weapon_conf = max(max_weapon_conf, conf)
        
        # Draw on frame
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
    time_diff = current_time - last_email_time
    
    print(f"DEBUG: Email Check - User: {user_email}, Poacher: {poacher_detected}, Weapon: {weapon_detected}, TimeDiff: {time_diff}, Cooldown: {EMAIL_COOLDOWN}")

    if (poacher_detected or weapon_detected) and (time_diff > EMAIL_COOLDOWN):
        print("DEBUG: Condition met! Attempting to send email...")
        temp_path = "temp_alert_frame.jpg"
        cv2.imwrite(temp_path, frame)
        subject = "EcoEye Alert: Poacher/Weapon Detected (Live)"
        
        # Get Real Location (IP-based)
        try:
            import requests
            # Short timeout to not block processing
            response = requests.get("https://ipinfo.io/json", timeout=2)
            data = response.json()
            loc = data.get("loc", "").split(",")
            if len(loc) == 2:
                lat, lng = loc[0], loc[1]
            else:
                raise Exception("Invalid location data")
        except Exception as e:
            print(f"Warning: Could not get real location ({e}). Using default.")
            lat, lng = "17.3850", "78.4867" # Default
        
        maps_link = f"https://www.google.com/maps/search/?api=1&query={lat},{lng}"
        
        body = f"Alert! Detection in live feed.\nPoacher: {poacher_detected}\nWeapon: {weapon_detected}"
        
        # Prioritize logged-in user's email
        recipient = user_email

        # Simple validation
        if "@" not in recipient:
            print(f"Warning: User '{recipient}' does not look like an email. Falling back to MAIL_RECIPIENT.")
            recipient = os.getenv("MAIL_RECIPIENT")

        if recipient:
            print(f"Sending email to {recipient} with location: {maps_link}")
            success = send_alert_email(temp_path, recipient, subject, body, location_link=maps_link)
            if success:
                print("DEBUG: Email sent successfully!")
                last_email_time = current_time
                mail_sent = True
            else:
                print("DEBUG: Email sending FAILED.")
        else:
            print("Error: No valid recipient email found.")
    else:
        print("DEBUG: Email condition NOT met (Cooldown or No Detection)")

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
            "mail": { "detected": mail_sent, "confidence": 1.0 if mail_sent else 0.0 },
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    }
