from pydantic import BaseModel, EmailStr
from datetime import datetime

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: str
    username: str
    email: EmailStr

class LoginResponse(BaseModel):
    token: str
    user: UserResponse

# New schema for chat messages
class Message(BaseModel):
    sender_id: str  # User ID of the sender
    receiver_id: str  # User ID of the receiver
    content: str  # Chat message content
    timestamp: datetime = datetime.now()
