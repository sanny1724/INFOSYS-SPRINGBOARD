from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

import certifi

load_dotenv()

MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = "ecoeye_db"

# Use certifi for TLS certificates (Required for some environments like Render)
client = AsyncIOMotorClient(MONGO_URL, tlsCAFile=certifi.where())
db = client[DB_NAME]

async def get_database():
    return db
