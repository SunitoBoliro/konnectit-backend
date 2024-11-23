from datetime import timedelta

from fastapi import HTTPException

from auth import create_access_token
from db import user_collection, serialize_user
from schemas import UserLogin
from utils import verify_password


async def login_user(user: UserLogin):
    db_user = await user_collection.find_one({"email": user.email})
    if not db_user or not verify_password(user.password, db_user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # Generate JWT token
    access_token_expires = timedelta(minutes=60)
    access_token = create_access_token(
        data={"sub": db_user["email"]}, expires_delta=access_token_expires
    )

    # Return token and user info
    return {
        "token": access_token,
        "user": serialize_user(db_user),
        "userId": str(db_user["_id"])  # Include user ID in the response
    }
