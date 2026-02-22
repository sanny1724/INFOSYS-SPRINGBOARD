from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

import certifi

load_dotenv()

MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = "ecoeye_db"

# Use certifi for TLS certificates (Required for some environments like Render)
# Added timeouts to avoid long hangs on "Processing..."
client = AsyncIOMotorClient(
    MONGO_URL, 
    tlsCAFile=certifi.where(),
    tls=True,
    serverSelectionTimeoutMS=5000, 
    connectTimeoutMS=5000
)
db = client[DB_NAME]

async def get_database():
    return db
