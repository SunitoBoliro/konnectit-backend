from fastapi import HTTPException

from db import user_collection, serialize_user
from models import User
from schemas import UserCreate
from utils import hash_password


async def register_user(user: UserCreate):
    existing_user = await user_collection.find_one({"email": user.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_password = hash_password(user.password)
    new_user = User(username=user.username, email=user.email, hashed_password=hashed_password, chats=[])
    result = await user_collection.insert_one(new_user.dict())
    return serialize_user({**new_user.dict(), "_id": result.inserted_id})
