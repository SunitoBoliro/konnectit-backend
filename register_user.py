from fastapi import HTTPException

from db import user_collection, serialize_user
from models import User
from schemas import UserCreate
from utils import hash_password
import base64



async def register_user(user: UserCreate):
    existing_user = await user_collection.find_one({"email": user.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    image_data = base64.b64decode(user.pp.split(',')[1])
    print(image_data) 

    hashed_password = hash_password(user.password)
    new_user = User(username=user.username, email=user.email, hashed_password=hashed_password, chats=[], pp=image_data)
    result = await user_collection.insert_one(new_user.dict())
    return serialize_user({**new_user.dict(), "_id": result.inserted_id})
