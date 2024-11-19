# auth.py
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from bson import ObjectId
from db import user_collection
from utils import hash_password, verify_password

# Secret key for signing the JWT
SECRET_KEY = "ahsanahmedkhan"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def validate_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            return {"isValid": False, "message": "Invalid token"}
        user = await user_collection.find_one({"email": email})  # Ensure this is awaited
        if not user:
            return {"isValid": False, "message": "User not found"}
        return {"isValid": True, "email": email, "user_id": str(user["_id"])}
    except JWTError as e:
        return {"isValid": False, "message": str(e)}