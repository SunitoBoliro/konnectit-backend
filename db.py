# db.py
from motor.motor_asyncio import AsyncIOMotorClient
from bson.objectid import ObjectId

# MongoDB Configuration
MONGO_URI = "mongodb://localhost:27017"  # Update with your MongoDB URI if using Atlas
client = AsyncIOMotorClient(MONGO_URI)
db = client["konnectit"]  # Database name
user_collection = db["usersreg"]
messages_collection = db["messages"]

# Helper function to parse MongoDB ObjectId
def serialize_user(user) -> dict:
    return {
        "id": str(user["_id"]),
        "username": user["username"],
        "email": user["email"]
    }
