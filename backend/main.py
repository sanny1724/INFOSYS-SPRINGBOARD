from fastapi import FastAPI, UploadFile, File, BackgroundTasks, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, validator
import shutil
import os
import time
import json
import detector # Import the detector module
from database import get_database
from auth import get_password_hash, verify_password, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES, SECRET_KEY, ALGORITHM
from jose import JWTError, jwt
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Wildeye AI Backend")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

class UserCreate(BaseModel):
    username: str
    password: str

    @validator('username')
    def username_must_be_email(cls, v):
        if '@' not in v or '.' not in v:
            raise ValueError('Username must be a valid email address')
        return v

@app.post("/auth/register")
async def register(user: UserCreate, db=Depends(get_database)):
    print(f"Attempting to register user: {user.username}")
    try:
        existing_user = await db.users.find_one({"username": user.username})
        if existing_user:
            print("User already exists")
            raise HTTPException(status_code=400, detail="Username already registered")
        
        hashed_password = get_password_hash(user.password)
        user_dict = {"username": user.username, "hashed_password": hashed_password}
        result = await db.users.insert_one(user_dict)
        print(f"User created with ID: {result.inserted_id}")
        return {"message": "User created successfully"}
    except Exception as e:
        print(f"ERROR during registration: {e}")
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")

@app.post("/auth/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db=Depends(get_database)):
    user = await db.users.find_one({"username": form_data.username})
    if not user or not verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["username"]}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

async def get_current_user(token: str = Depends(oauth2_scheme), db=Depends(get_database)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = await db.users.find_one({"username": username})
    if user is None:
        raise credentials_exception
    
    # Return user details
    return {
        "username": user["username"], 
        "_id": str(user["_id"]),
        "name": user.get("name", "User"),
        "picture": user.get("picture"),
        "created_at": user.get("created_at")
    }

@app.get("/users/me")
async def read_users_me(current_user: dict = Depends(get_current_user)):
    return current_user

@app.on_event("startup")
async def startup_event():
    print(">>> BACKEND SERVER ON PORT 8001 STARTED <<<", flush=True)

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
async def upload_video(file: UploadFile = File(...), background_tasks: BackgroundTasks = None, current_user: dict = Depends(get_current_user)):
    print(f"DEBUG: Upload request received. Filename: '{file.filename}'", flush=True)
    file_location = f"{UPLOAD_DIR}/{file.filename}"
    print(f"DEBUG: Saving to {file_location}", flush=True)
    with open(file_location, "wb+") as file_object:
        shutil.copyfileobj(file.file, file_object)
    print(f"DEBUG: File saved. Size: {os.path.getsize(file_location)} bytes", flush=True)
    
    # Trigger processing in background
    if background_tasks:
        print(f"DEBUG: Adding background task for {file_location}", flush=True)
        background_tasks.add_task(detector.process_video, file_location, current_user["username"])
    else:
        print("ERROR: No background_tasks object!", flush=True)
        
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
            
    # Check if original file exists
    file_path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(file_path):
        return {"status": "error", "message": "File not found on server"}
    
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
async def detect_frame(file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    print(">>> REQUEST RECEIVED at /detect_frame <<<", flush=True)
    try:
        image_bytes = await file.read()
        # Call the process_frame function from detector module
        results = detector.process_frame(image_bytes, current_user["username"])
        return results
    except Exception as e:
        print(f"Error in detect_frame: {e}")
        return {"error": str(e)}
import httpx

# OAuth Configuration
# OAuth Configuration
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8001/callback/google")

print(f"DEBUG: Loaded GOOGLE_CLIENT_ID: {GOOGLE_CLIENT_ID}")

GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET")
GITHUB_REDIRECT_URI = os.getenv("GITHUB_REDIRECT_URI", "http://localhost:8000/callback/github")

@app.get("/login/google")
async def login_google():
    auth_url = f"https://accounts.google.com/o/oauth2/auth?response_type=code&client_id={GOOGLE_CLIENT_ID}&redirect_uri={GOOGLE_REDIRECT_URI}&scope=openid%20profile%20email&access_type=offline"
    print(f"DEBUG: Generated Google Auth URL: {auth_url}")
    return {
        "url": auth_url
    }

@app.get("/callback/google")
async def callback_google(code: str, db=Depends(get_database)):
    token_url = "https://accounts.google.com/o/oauth2/token"
    data = {
        "code": code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code",
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(token_url, data=data)
        access_token = response.json().get("access_token")
        
        user_info = await client.get("https://www.googleapis.com/oauth2/v1/userinfo", headers={"Authorization": f"Bearer {access_token}"})
        user_data = user_info.json()
        
        email = user_data.get("email")
        name = user_data.get("name")
        picture = user_data.get("picture")
        
        # Check if user exists, if not create
        user = await db.users.find_one({"username": email})
        if not user:
            user_dict = {
                "username": email, 
                "hashed_password": "oauth_user",
                "name": name,
                "picture": picture,
                "created_at": datetime.now().strftime("%Y-%m-%d")
            }
            await db.users.insert_one(user_dict)
        else:
            # Update existing user with latest info
            await db.users.update_one(
                {"username": email},
                {"$set": {"name": name, "picture": picture}}
            )
            
        # Create token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": email}, expires_delta=access_token_expires
        )
        
        # Redirect to frontend with token
        frontend_url = f"http://localhost:5173/login?token={access_token}"
        return RedirectResponse(url=frontend_url)

@app.post("/users/me/avatar")
async def upload_avatar(file: UploadFile = File(...), current_user: dict = Depends(get_current_user), db=Depends(get_database)):
    try:
        # Create unique filename
        file_extension = os.path.splitext(file.filename)[1]
        filename = f"avatar_{current_user['username']}_{int(time.time())}{file_extension}"
        file_location = f"{UPLOAD_DIR}/{filename}"
        
        with open(file_location, "wb+") as file_object:
            shutil.copyfileobj(file.file, file_object)
            
        # URL for the uploaded avatar
        avatar_url = f"http://localhost:8000/uploads/{filename}"
        
        # Update user in DB
        await db.users.update_one(
            {"username": current_user["username"]},
            {"$set": {"picture": avatar_url}}
        )
        
        return {"info": "Avatar updated successfully", "picture": avatar_url}
        
    except Exception as e:
        print(f"Error uploading avatar: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload avatar")

@app.get("/login/github")
async def login_github():
    return {
        "url": f"https://github.com/login/oauth/authorize?client_id={GITHUB_CLIENT_ID}&redirect_uri={GITHUB_REDIRECT_URI}&scope=user:email"
    }

@app.get("/callback/github")
async def callback_github(code: str, db=Depends(get_database)):
    token_url = "https://github.com/login/oauth/access_token"
    data = {
        "client_id": GITHUB_CLIENT_ID,
        "client_secret": GITHUB_CLIENT_SECRET,
        "code": code,
    }
    headers = {"Accept": "application/json"}
    
    async with httpx.AsyncClient() as client:
        response = await client.post(token_url, data=data, headers=headers)
        access_token = response.json().get("access_token")
        
        user_info = await client.get("https://api.github.com/user", headers={"Authorization": f"Bearer {access_token}"})
        user_data = user_info.json()
        
        username = user_data.get("login")
        
        # Check if user exists
        user = await db.users.find_one({"username": username})
        if not user:
             user_dict = {"username": username, "hashed_password": "oauth_user"}
             await db.users.insert_one(user_dict)
             
        # Create token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": username}, expires_delta=access_token_expires
        )
        
        return {"access_token": access_token, "token_type": "bearer", "redirect": f"http://localhost:5173/login?token={access_token}"}
