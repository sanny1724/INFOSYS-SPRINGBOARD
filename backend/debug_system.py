import os
from ultralytics import YOLO
from dotenv import load_dotenv
from mailer import send_alert_email
import cv2
import numpy as np

load_dotenv()

print("=== SYSTEM DIAGNOSTIC ===")

# 1. Check Model
model_path = r"C:\Users\sravs\.gemini\antigravity\scratch\wildeye_ai\backend\runs\detect\train2\weights\best.pt"
print(f"\n[1] Checking Model at: {model_path}")
if os.path.exists(model_path):
    print("    -> File exists.")
    try:
        model = YOLO(model_path)
        print("    -> Model loaded successfully.")
        print(f"    -> Model Classes: {model.names}")
    except Exception as e:
        print(f"    -> ERROR loading model: {e}")
else:
    print("    -> ERROR: Model file NOT found!")

# 2. Check Email
print("\n[2] Checking Email Configuration")
user = os.getenv("MAIL_USERNAME")
pw = os.getenv("MAIL_PASSWORD")
recip = os.getenv("MAIL_RECIPIENT")

print(f"    -> MAIL_USERNAME: {user}")
print(f"    -> MAIL_PASSWORD: {'*' * len(pw) if pw else 'MISSING'}")
print(f"    -> MAIL_RECIPIENT: {recip}")

if user and pw and recip:
    print("    -> Attempting to send test email...")
    # Create dummy image
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    cv2.imwrite("diag_test.jpg", img)
    
    try:
        success = send_alert_email("diag_test.jpg", recip, "Diagnostic Test", "This is a test from the debug script.")
        if success:
            print("    -> Email sent SUCCESSFULLY.")
        else:
            print("    -> Email FAILED to send.")
    except Exception as e:
        print(f"    -> Email ERROR: {e}")
else:
    print("    -> Skipping email test: Missing credentials.")

print("\n=== END DIAGNOSTIC ===")
