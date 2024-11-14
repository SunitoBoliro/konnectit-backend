# main.py
from fastapi import FastAPI, HTTPException, Depends
from models import User
from schemas import UserCreate, UserLogin, UserResponse
from db import user_collection, serialize_user
from auth import hash_password, verify_password
from bson import ObjectId

app = FastAPI()

@app.post("/register", response_model=UserResponse)
async def register_user(user: UserCreate):
    # Check if user already exists
    existing_user = await user_collection.find_one({"email": user.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Hash the password and store user
    hashed_password = hash_password(user.password)
    new_user = User(username=user.username, email=user.email, hashed_password=hashed_password)
    result = await user_collection.insert_one(new_user.dict())
    return serialize_user({**new_user.dict(), "_id": result.inserted_id})

@app.post("/login", response_model=UserResponse)
async def login_user(user: UserLogin):
    # Check if user exists
    db_user = await user_collection.find_one({"email": user.email})
    if not db_user or not verify_password(user.password, db_user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # Return user information
    return serialize_user(db_user)
