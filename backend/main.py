from fastapi import FastAPI, UploadFile, File, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import shutil
import os
import json
import detector # Import the detector module

app = FastAPI(title="Wildeye AI Backend")

@app.on_event("startup")
async def startup_event():
    print(">>> BACKEND RENDERING SERVER STARTED <<<", flush=True)

# CORS Setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "../uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Serve uploaded/processed files
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# Mount static files (Frontend)
# Ensure 'frontend/dist' exists (run npm run build first)
if os.path.exists("../frontend/dist"):
    app.mount("/assets", StaticFiles(directory="../frontend/dist/assets"), name="assets")

# Serve React App
@app.get("/")
async def serve_frontend():
    if os.path.exists("../frontend/dist/index.html"):
        return FileResponse("../frontend/dist/index.html")
    return {"error": "Frontend not built. Run 'npm run build' in frontend directory."}

@app.post("/upload")
async def upload_video(file: UploadFile = File(...), background_tasks: BackgroundTasks = None):
    file_location = f"{UPLOAD_DIR}/{file.filename}"
    with open(file_location, "wb+") as file_object:
        shutil.copyfileobj(file.file, file_object)
    
    # Trigger processing in background
    if background_tasks:
        background_tasks.add_task(detector.process_video, file_location)
        
    return {"info": f"file '{file.filename}' saved at '{file_location}'", "status": "processing_started"}

@app.get("/results/{filename}")
async def get_results(filename: str):
    # Construct expected JSON path
    # If filename is "image.png", json is "processed_image.json"
    base_name = os.path.splitext(filename)[0]
    json_filename = f"processed_{base_name}.json"
    json_path = os.path.join(UPLOAD_DIR, json_filename)
    
    if os.path.exists(json_path):
        with open(json_path, "r") as f:
            return json.load(f)
    
    return {"status": "processing"}

@app.websocket("/ws/detect")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print(">>> WEBSOCKET CONNECTED <<<", flush=True)
    try:
        while True:
            data = await websocket.receive_bytes()
            # Process frame
            results = detector.process_frame(data)
            # Send back JSON
            await websocket.send_json(results)
    except WebSocketDisconnect:
        print(">>> WEBSOCKET DISCONNECTED <<<", flush=True)
    except Exception as e:
        print(f"WebSocket Error: {e}", flush=True)

@app.post("/detect_frame")
async def detect_frame(file: UploadFile = File(...)):
    print(">>> REQUEST RECEIVED at /detect_frame <<<", flush=True)
    try:
        image_bytes = await file.read()
        # Call the process_frame function from detector module
        results = detector.process_frame(image_bytes)
        return results
    except Exception as e:
        print(f"Error in detect_frame: {e}")
        return {"error": str(e)}
