"""
MongoDB Database Connection
"""
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ConnectionFailure
import os

MONGO_URL = os.getenv("MONGODB_URI", os.getenv("MONGO_URL", "mongodb://localhost:27017"))
DATABASE_NAME = os.getenv("DATABASE_NAME", "quiz_battle")

client: AsyncIOMotorClient = None
db = None


async def connect_to_mongo():
    """Connect to MongoDB"""
    global client, db
    try:
        client = AsyncIOMotorClient(MONGO_URL)
        db = client[DATABASE_NAME]
        # Verify connection
        await client.admin.command('ping')
        print(f"✅ Connected to MongoDB: {DATABASE_NAME}")
    except ConnectionFailure as e:
        print(f"❌ MongoDB connection failed: {e}")
        raise


async def close_mongo_connection():
    """Close MongoDB connection"""
    global client
    if client:
        client.close()
        print("🔌 MongoDB connection closed")


def get_database():
    """Get database instance"""
    return db


async def init_competition_collections():
    """Initialize competition collections with indexes"""
    if db is None:
        return
    
    # Competition rooms collection
    await db.competition_rooms.create_index("room_code", unique=True)
    await db.competition_rooms.create_index("session_id")
    await db.competition_rooms.create_index("status")
    await db.competition_rooms.create_index("created_by")
    
    # Competition participants collection
    await db.competition_participants.create_index([("room_id", 1), ("student_id", 1)], unique=True)
    await db.competition_participants.create_index("room_id")
    await db.competition_participants.create_index("student_id")
    
    # Competition answers collection
    await db.competition_answers.create_index([("room_id", 1), ("student_id", 1), ("question_index", 1)], unique=True)
    await db.competition_answers.create_index("room_id")
    
    # Student questions collection (AI generated)
    await db.student_questions.create_index("session_id")
    await db.student_questions.create_index("created_by")
    
    print("✅ Competition collections initialized")
