"""
MongoDB Database Connection
"""
from motor.motor_asyncio import AsyncIOMotorClient
from backend.core.config import settings

class Database:
    client: AsyncIOMotorClient = None

db = Database()


async def connect_to_mongo():
    """Create database connection"""
    db.client = AsyncIOMotorClient(settings.MONGODB_URL)
    print(f"Connected to MongoDB: {settings.MONGODB_DB_NAME}")


async def close_mongo_connection():
    """Close database connection"""
    if db.client:
        db.client.close()
        print("Disconnected from MongoDB")


def get_database():
    """Get database instance"""
    return db.client[settings.MONGODB_DB_NAME]
