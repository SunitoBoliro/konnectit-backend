from motor.motor_asyncio import AsyncIOMotorClient
from bson.objectid import ObjectId
from models import User, Message, PyObjectId
import logging
from os import getenv
from dotenv import load_dotenv
from utils import hash_password

load_dotenv()

# MongoDB Configuration
MONGO_URI = getenv("MONGO_URI", "mongodb://localhost:27017")  # Update with your MongoDB URI if using Atlas
client = AsyncIOMotorClient(MONGO_URI)
db = client["konnectit"]  # Database name
user_collection = db["usersreg"]
message_collection = db["messages"]
# calls_collection = db["calls"]
call_logs_collection = db['CallLogs']


def serialize_user(user):
    return {
        "id": str(user["_id"]),
        "username": user["username"],
        "email": user["email"],
        "chats": [str(chat) for chat in user.get("chats", [])],
        "pp": str(user["pp"])
    }


def serialize_message(message):
    return {
        "id": str(message["_id"]),
        "type": str(message["type"]),
        "chatId": str(message["chatId"]),
        "content": str(message["content"]),
        "timestamp": str(message["timestamp"]),
        "sender": str(message["sender"]),

    }


async def seed_users():
    # Example users
    users = [
        {
            "username": "Alice",
            "email": "alice@example.com",
            "hashed_password": hash_password("password123"),
            "chats": []
        },
        {
            "username": "Bob",
            "email": "bob@example.com",
            "hashed_password": hash_password("password123"),
            "chats": []
        },
        {
            "username": "Charlie",
            "email": "charlie@example.com",
            "hashed_password": hash_password("password123"),
            "chats": []
        }
    ]

    # Insert users into the database
    for user in users:
        existing_user = await user_collection.find_one({"email": user["email"]})
        if not existing_user:
            await user_collection.insert_one(user)
            logging.info(f"Inserted user: {user['email']}")

    logging.info("Seeding complete")