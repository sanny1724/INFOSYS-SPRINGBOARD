import cv2
import os
import json
import time
from mailer import send_alert_email
import numpy as np
import base64
import datetime
import random
from pathlib import Path

# Speed Optimization Constants
FRAME_SKIP = 6  # Process every 6th frame
INFERENCE_SIZE = 320 # Smaller size for speed

# Global model variables
model = None
model_error = None
detector_initialized = False

def get_model():
    global model, model_error, detector_initialized
    if detector_initialized:
        return model, model_error
    
    detector_initialized = True
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    model_path = os.path.join(BASE_DIR, "best.pt")
    
    print(f"DEBUG: Lazy Loading model from: {model_path}", flush=True)
    try:
        from ultralytics import YOLO # Heavy import moved here
        if os.path.exists(model_path):
            model = YOLO(model_path)
            print(">>> SUCCESS: YOLO model loaded <<<", flush=True)
        else:
            model_error = f"Model file not found at {model_path}"
            print(f"ERROR: {model_error}", flush=True)
    except Exception as e:
        model_error = str(e)
        print(f"ERROR: Failed to load YOLO model: {e}", flush=True)
    
    return model, model_error

# For backward compatibility if needed at the top level
model_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "best.pt")

# Global variable for rate limiting
last_email_time = 0
EMAIL_COOLDOWN = 60 # Seconds

def process_video(video_path: str, user_email: str):
    print(f"DEBUG [v3.3]: process_video STARTED for {video_path}", flush=True)
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
            t_start = time.time()
            m, _ = get_model()
            
            if m is None:
                print("DEBUG: Model is None, skipping analysis", flush=True)
                results = []
            else:
                results = m(frame, conf=0.15, imgsz=480)
                t_inference = time.time() - t_start
                print(f"DEBUG: Inference took {t_inference:.2f}s (imgsz=480)", flush=True)
            
            # Robust check for results
            if m and results and len(results) > 0 and results[0] is not None:
                res = results[0]
                # Check for boxes safely
                if hasattr(res, 'boxes') and res.boxes is not None:
                    print(f"DEBUG: Processing {len(res.boxes)} found boxes", flush=True)
                    for box in res.boxes:
                        # ULTRA DEFENSIVE: Check if xyxy exists and has data
                        if not hasattr(box, 'xyxy') or box.xyxy is None or len(box.xyxy) == 0:
                            continue
                            
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        cls = int(box.cls[0]) if (hasattr(box, 'cls') and box.cls is not None and len(box.cls) > 0) else 0
                        conf = float(box.conf[0]) if (hasattr(box, 'conf') and box.conf is not None and len(box.conf) > 0) else 0.0
                        
                        label_names = getattr(m, 'names', {})
                        label = label_names.get(cls, f"Object {cls}")
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
            # Video Branch also needs guards
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                raise Exception("Error opening video file")
            
            width, height, fps = int(cap.get(3)), int(cap.get(4)), int(cap.get(5))
            out = cv2.VideoWriter(output_path, cv2.VideoWriter_fourcc(*'mp4v'), fps, (width, height))
            
            m, _ = get_model()
            frame_count = 0
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret: break
                
                frame_count += 1
                if frame_count % FRAME_SKIP != 0:
                    continue  # Skip this frame
                
                if m is None:
                    out.write(frame); continue
                    
                results = m(frame, conf=0.25, imgsz=INFERENCE_SIZE)
                if results and len(results) > 0 and results[0] is not None:
                    annotated = results[0].plot()
                    out.write(annotated)
                    if hasattr(results[0], 'boxes') and results[0].boxes is not None:
                        for box in results[0].boxes:
                            if not hasattr(box, 'cls') or box.cls is None or len(box.cls) == 0: continue
                            cls, conf = int(box.cls[0]), float(box.conf[0])
                            if cls == 0: poacher_detected, max_poacher_conf = True, max(max_poacher_conf, conf)
                            if cls in [2, 3]: weapon_detected, max_weapon_conf = True, max(max_weapon_conf, conf)
                else:
                    out.write(frame)
            cap.release(); out.release()
            
        mail_sent_status = "No"
        if poacher_detected or weapon_detected:
            recipient = user_email if (user_email and "@" in user_email) else os.getenv("MAIL_RECIPIENT")
            if recipient:
                print(f"🛡️ DEBUG: Sending Alert Email to: {recipient}", flush=True)
                success, msg = send_alert_email(output_path, recipient)
                mail_sent_status = "Yes" if success else f"Failed: {msg}"
                
        results_data = {
            "status": "completed",
            "poacher_detected": poacher_detected,
            "weapon_detected": "Yes" if weapon_detected else "No",
            "poacher_confidence": round(max_poacher_conf * 100, 1),
            "weapon_confidence": round(max_weapon_conf * 100, 1),
            "mail_sent": mail_sent_status,
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "video_url": f"/uploads/{os.path.basename(output_path)}",
            "detections": detections if is_image else []
        }
        with open(json_path, "w") as f: json.dump(results_data, f)
    except Exception as e:
        print(f"Error in process_video: {e}", flush=True)
        import traceback
        traceback.print_exc()
        with open(json_path, "w") as f: json.dump({"status": "error", "message": f"Analysis crashed: {str(e)}"}, f)

def process_frame(image_bytes, user_email: str):
    global last_email_time
    try:
        nparr = np.frombuffer(image_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if frame is None: return {"error": "Could not decode image"}
        
        t_start = time.time()
        m, _ = get_model()
        
        if m is None:
            return {"status": "error", "message": "Detection model not loaded"}
            
        results = m(frame, conf=0.15, imgsz=480)
        t_inference = time.time() - t_start
        print(f"DEBUG: Frame Inference took {t_inference:.2f}s", flush=True)
        
        detections, poacher_detected, weapon_detected = [], False, False
        max_poacher_conf, max_weapon_conf = 0.0, 0.0
        
        if results and len(results) > 0 and results[0] is not None:
            res = results[0]
            if hasattr(res, 'boxes') and res.boxes is not None:
                for box in res.boxes:
                    if not hasattr(box, 'xyxy') or box.xyxy is None or len(box.xyxy) == 0: continue
                    
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    cls = int(box.cls[0]) if (hasattr(box, 'cls') and box.cls is not None and len(box.cls) > 0) else 0
                    conf = float(box.conf[0]) if (hasattr(box, 'conf') and box.conf is not None and len(box.conf) > 0) else 0.0
                    
                    label_names = getattr(m, 'names', {})
                    label, color, valid = label_names.get(cls, f"Object {cls}"), (255, 255, 255), False
                    
                    if cls == 0: 
                        label, color, valid, poacher_detected = "Poacher", (0, 0, 255), True, True
                        max_poacher_conf = max(max_poacher_conf, conf)
                    elif cls == 1: 
                        label, color, valid = "Ranger", (0, 255, 0), True
                    elif cls == 2 or cls == 3: 
                        label, color, valid, weapon_detected = "Weapon", (0, 0, 255), True, True
                        max_weapon_conf = max(max_weapon_conf, conf)
                    
                    if valid:
                        detections.append({"box": [x1, y1, x2, y2], "class_id": cls, "label": label, "confidence": conf})
                        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                        cv2.putText(frame, f"{label} {int(conf*100)}%", (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                
        mail_sent_status = "No"
        if (poacher_detected or weapon_detected) and (time.time() - last_email_time > EMAIL_COOLDOWN):
            temp_path = os.path.abspath("temp_alert_frame.jpg")
            cv2.imwrite(temp_path, frame)
            recipient = user_email if (user_email and "@" in user_email) else os.getenv("MAIL_RECIPIENT")
            if recipient:
                print(f"🛡️ DEBUG: Sending Live Alert Email to: {recipient}", flush=True)
                success, msg = send_alert_email(temp_path, recipient)
                if success:
                    mail_sent_status, last_email_time = "Yes", time.time()
                else:
                    mail_sent_status = f"Failed: {msg}"
                    
        _, buffer = cv2.imencode('.jpg', frame)
        return {
            "status": "completed",
            "image": f"data:image/jpeg;base64,{base64.b64encode(buffer).decode('utf-8')}",
            "detections": detections,
            "summary": {
                "poacher": {"detected": poacher_detected, "confidence": max_poacher_conf},
                "weapon": {"detected": weapon_detected, "confidence": max_weapon_conf},
                "mail": {"detected": mail_sent_status, "confidence": 1.0 if mail_sent_status == "Yes" else 0.0},
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        }
    except Exception as e:
        print(f"Error in process_frame: {e}", flush=True)
        return {"error": f"Frame analysis failed: {str(e)}"}
