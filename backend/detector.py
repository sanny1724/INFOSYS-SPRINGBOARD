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
# In production, we use a static path to the unignored model file
base_dir = os.path.dirname(__file__)
model_path = os.path.abspath(os.path.join(base_dir, "models", "best.pt"))

# Fallback for local development
if not os.path.exists(model_path):
    model_path = os.path.abspath(os.path.join(base_dir, "runs", "detect", "train2", "weights", "best.pt"))

print(f"Loading model from: {model_path}")
model = YOLO(model_path)

# Global variable for rate limiting
last_email_time = 0
EMAIL_COOLDOWN = 60 # Seconds

def process_video(video_path: str, user_email: str):
    print(f"DEBUG: process_video STARTED for {video_path}", flush=True)
    video_path = os.path.abspath(video_path)
    filename = os.path.basename(video_path)
    is_image = filename.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.webp'))
    
    output_path = video_path.replace(filename, f"processed_{filename}")
    json_path = output_path.replace(os.path.splitext(output_path)[1], '.json')
    
    poacher_detected = False
    weapon_detected = False
    max_poacher_conf = 0.0
    max_weapon_conf = 0.0
    detections = []
    
    try:
        if is_image:
            frame = cv2.imread(video_path)
            if frame is None:
                raise Exception(f"Could not open image file: {video_path}")
            
            annotated_frame = frame.copy()
            results = model(frame, conf=0.15)
            
            for box in results[0].boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                cls = int(box.cls[0])
                conf = float(box.conf[0])
                label = model.names[cls]
                color = (255, 255, 255)
                
                valid = False
                if cls == 0 and conf > 0.15: # Poacher
                    label, color, valid, poacher_detected = "Poacher", (0, 0, 255), True, True
                    max_poacher_conf = max(max_poacher_conf, conf)
                elif cls == 1 and conf > 0.35: # Ranger
                    label, color, valid = "Ranger", (0, 255, 0), True
                elif cls == 2 and conf > 0.15: # Weapon
                    label, color, valid, weapon_detected = "Weapon", (0, 0, 255), True, True
                    max_weapon_conf = max(max_weapon_conf, conf)
                elif cls == 3 and conf > 0.15: # WW
                    label, color, valid, weapon_detected = "WW", (0, 165, 255), True, True
                    max_weapon_conf = max(max_weapon_conf, conf)
                
                if valid:
                    detections.append({"box": [x1, y1, x2, y2], "class_id": cls, "label": label, "confidence": conf})
                    cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, 2)
                    cv2.putText(annotated_frame, f"{label} {int(conf*100)}%", (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2)
            
            cv2.imwrite(output_path, annotated_frame)
        else:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                raise Exception("Error opening video file")
            
            width, height, fps = int(cap.get(3)), int(cap.get(4)), int(cap.get(5))
            out = cv2.VideoWriter(output_path, cv2.VideoWriter_fourcc(*'mp4v'), fps, (width, height))
            
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret: break
                results = model(frame, conf=0.25)
                out.write(results[0].plot())
                for box in results[0].boxes:
                    cls, conf = int(box.cls[0]), float(box.conf[0])
                    if cls == 0: poacher_detected, max_poacher_conf = True, max(max_poacher_conf, conf)
                    if cls in [2, 3]: weapon_detected, max_weapon_conf = True, max(max_weapon_conf, conf)
            cap.release(); out.release()
            
        mail_sent = False
        if poacher_detected or weapon_detected:
            recipient = user_email if "@" in user_email and user_email != "ranger_dev@wildeye.ai" else os.getenv("MAIL_RECIPIENT")
            if recipient:
                mail_sent = send_alert_email(output_path, recipient)
                
        results_data = {
            "status": "completed",
            "poacher_detected": poacher_detected,
            "weapon_detected": "Yes" if weapon_detected else "No",
            "poacher_confidence": round(max_poacher_conf * 100, 1),
            "weapon_confidence": round(max_weapon_conf * 100, 1),
            "mail_sent": "Yes" if mail_sent else "No",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "video_url": f"/uploads/{os.path.basename(output_path)}",
            "detections": detections if is_image else []
        }
        with open(json_path, "w") as f: json.dump(results_data, f)
    except Exception as e:
        print(f"Error: {e}")
        with open(json_path, "w") as f: json.dump({"status": "error", "message": str(e)}, f)

def process_frame(image_bytes, user_email: str):
    global last_email_time
    nparr = np.frombuffer(image_bytes, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if frame is None: return {"error": "Could not decode image"}
    
    results = model(frame, conf=0.15)
    detections, poacher_detected, weapon_detected = [], False, False
    max_poacher_conf, max_weapon_conf = 0.0, 0.0
    
    for box in results[0].boxes:
        x1, y1, x2, y2 = map(int, box.xyxy[0])
        cls, conf = int(box.cls[0]), float(box.conf[0])
        label, color, valid = model.names[cls], (255, 255, 255), False
        
        if cls == 0: label, color, valid, poacher_detected = "Poacher", (0, 0, 255), True, True; max_poacher_conf = max(max_poacher_conf, conf)
        elif cls == 1: label, color, valid = "Ranger", (0, 255, 0), True
        elif cls == 2: label, color, valid, weapon_detected = "Weapon", (0, 0, 255), True, True; max_weapon_conf = max(max_weapon_conf, conf)
        elif cls == 3: label, color, valid, weapon_detected = "WW", (0, 165, 255), True, True; max_weapon_conf = max(max_weapon_conf, conf)
        
        if valid:
            detections.append({"box": [x1, y1, x2, y2], "class_id": cls, "label": label, "confidence": conf})
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(frame, f"{label} {int(conf*100)}%", (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
            
    mail_sent = False
    if (poacher_detected or weapon_detected) and (time.time() - last_email_time > EMAIL_COOLDOWN):
        temp_path = os.path.abspath("temp_alert_frame.jpg")
        cv2.imwrite(temp_path, frame)
        recipient = user_email if "@" in user_email and user_email != "ranger_dev@wildeye.ai" else os.getenv("MAIL_RECIPIENT")
        if recipient:
            if send_alert_email(temp_path, recipient):
                mail_sent, last_email_time = True, time.time()
                
    _, buffer = cv2.imencode('.jpg', frame)
    return {
        "status": "completed",
        "image": f"data:image/jpeg;base64,{base64.b64encode(buffer).decode('utf-8')}",
        "detections": detections,
        "summary": {
            "poacher": {"detected": poacher_detected, "confidence": max_poacher_conf},
            "weapon": {"detected": weapon_detected, "confidence": max_weapon_conf},
            "mail": {"detected": mail_sent, "confidence": 1.0 if mail_sent else 0.0},
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    }
