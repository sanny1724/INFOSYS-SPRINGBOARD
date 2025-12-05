import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os

async def test_mongo():
    try:
        print("Attempting to connect to MongoDB...")
        client = AsyncIOMotorClient("mongodb://localhost:27017", serverSelectionTimeoutMS=2000)
        await client.server_info()
        print("SUCCESS: Connected to MongoDB!")
    except Exception as e:
        print(f"FAILURE: Could not connect to MongoDB. Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_mongo())
