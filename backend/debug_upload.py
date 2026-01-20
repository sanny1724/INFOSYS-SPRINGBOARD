import os
import sys
sys.path.append(os.getcwd())
from detector import process_video

# The user's uploaded file is likely in the artifacts directory, but I need to copy it to uploads to process it like the app does.
# Or I can just process it directly from where it is if I know the path.
# The user metadata says: C:/Users/sravs/.gemini/antigravity/brain/8084a84e-06ab-4cd0-92d2-664ed9cdbd64/uploaded_image_1764479773144.png

image_path = "C:/Users/sravs/.gemini/antigravity/brain/8084a84e-06ab-4cd0-92d2-664ed9cdbd64/uploaded_image_1764479773144.png"

if os.path.exists(image_path):
    print(f"Running detection on {image_path}...")
    process_video(image_path)
else:
    print(f"File not found: {image_path}")
