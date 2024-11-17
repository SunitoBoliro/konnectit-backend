from fastapi import FastAPI, HTTPException, Depends, Body, Request ,WebSocket, WebSocketDisconnect
from models import User
from schemas import UserCreate, UserLogin, UserResponse
from db import user_collection, serialize_user , messages_collection
from auth import hash_password, verify_password, generate_token, validate_token
from bson import ObjectId
from fastapi.middleware.cors import CORSMiddleware
import hashlib
import time
from pydantic import BaseModel
from fastapi.responses import HTMLResponse
from typing import List, Dict

from fastapi import FastAPI, HTTPException, Body
import hashlib
import time

app = FastAPI()

# CORS configuration remains the same
origins = [
    "http://localhost:5173",
    "http://192.168.18.232:5173",
    "https://your-frontend-domain.com",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


chats = [
    {"id": 1, "name": "Chat 1", "message": "Hello!", "time": "10:00 AM"},
    {"id": 2, "name": "Chat 2", "message": "Hi there!", "time": "10:05 AM"},
]

messages = {
    1: [{"sender": "user", "text": "Hi!"}, {"sender": "bot", "text": "How can I assist you?"}],
    2: [{"sender": "user", "text": "Hello!"}, {"sender": "bot", "text": "How are you?"}],
}




@app.post("/register", response_model=UserResponse)
async def register_user(user: UserCreate):
    existing_user = await user_collection.find_one({"email": user.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_password = hash_password(user.password)
    new_user = User(username=user.username, email=user.email, hashed_password=hashed_password)
    result = await user_collection.insert_one(new_user.dict())
    return serialize_user({**new_user.dict(), "_id": result.inserted_id})

@app.post("/login")
async def login_user(user: UserLogin):
    db_user = await user_collection.find_one({"email": user.email})
    if not db_user or not verify_password(user.password, db_user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # Generate SHA1 token
    token = generate_token(db_user["email"])

    # Return token and user info
    return {
        "token": token,
        "user": serialize_user(db_user)
    }


class TokenRequest(BaseModel):
    token: str  # Expecting a single field 'token' as a string


@app.get("/validate")
async def validate_token(request: Request):
    try:
        token = request.query_params.get('token')  # Get the token from query parameters
        if not token:
            return {"isValid": False, "message": "Token is missing"}

        token_parts = token.split(":")  # Format: sha1:expiry
        if len(token_parts) != 2:
            raise ValueError("Invalid token format")
        
        sha1_hash, expiry = token_parts
        if time.time() > float(expiry):
            return {"isValid": False}

        # Optionally verify the hash logic (depends on your implementation)
        return {"isValid": True}
    except Exception as e:
        return {"isValid": False, "message": str(e)}
    



# Define the message model for sending messages
class Message(BaseModel):
    message: str

# API to fetch all chats
@app.get("/chats")
async def get_chats():
    return chats

# API to send a message to a specific chat
@app.post("/chats/{chat_id}/messages")
async def send_message(chat_id: int, message: Message):
    if chat_id not in messages:
        messages[chat_id] = []
    messages[chat_id].append({"sender": "user", "text": message.message})
    # Simulate a bot reply
    bot_reply = "Bot reply to: " + message.message
    messages[chat_id].append({"sender": "bot", "text": bot_reply})
    return {"reply": bot_reply}

    
connected_clients = []
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_clients.append(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            messages_collection.insert_one(data)  # Store in DB
            for client in connected_clients:
                await client.send_json(data)
    except WebSocketDisconnect:
        connected_clients.remove(websocket)