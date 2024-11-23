# main.py
import asyncio
import logging
from datetime import datetime
from typing import List, Dict

from fastapi import FastAPI, HTTPException, WebSocket, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import EmailStr
from sse_starlette import EventSourceResponse

from db import user_collection, serialize_user
from get_current_user import get_current_user
from get_messages import get_messages
from login_user import login_user
from models import User
from register_user import register_user
from schemas import UserResponse, UserCreate, UserLogin
from validate_token_endpoint import validate_token_endpoint
from websocket_config import websocket_endpoint, user_status

app = FastAPI()

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# CORS configuration
origins = [
    "http://localhost:5173",
    "http://192.168.18.232:5173",
    "http://192.168.23.107:5173/",
    "https://your-frontend-domain.com",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# @app.on_event("startup")
# async def startup_event():
#     await seed_users()

active_connections: Dict[EmailStr, WebSocket] = {}
# user_status: Dict[EmailStr, dict] = {}  # Tracks online status and last seen time
active_webrtc_connections: Dict[str, WebSocket] = {}
webrtc_sessions: Dict[str, Dict[EmailStr, bool]] = {}

@app.post("/register", response_model=UserResponse)
async def register(user: UserCreate):
    return await register_user(user)


@app.post("/login")
async def login(user: UserLogin):
    return await login_user(user)


@app.get("/validate")
async def validate_token(token: str = Query(...)):
    return await validate_token_endpoint(token)


@app.websocket("/ws/{token}")
async def websocket_communication(websocket: WebSocket, token: str):
    return await websocket_endpoint(websocket, token)


# @app.websocket("/webrtc/{token}")
# async def webrtc_websocket_connection(websocket: WebSocket, token: str):
#     await webrtc_websocket_endpoint(websocket, token)


@app.get("/user-status/{email}")
async def get_user_status(email: EmailStr):
    """API to get a user's online status and last seen time."""
    logging.debug(f"User Status=> {user_status}")
    if email in user_status:
        stats = user_status[email]
        logging.debug(f"Stats=> {stats}")
        return {
            "online": stats["online"],
            "last_seen": stats["last_seen"].isoformat() if stats["last_seen"] else None,
        }
    else:
        raise HTTPException(status_code=404, detail="User not found")


@app.get("/sse/user-status/{email}")
async def sse_user_status(email: EmailStr):
    async def event_generator():
        while True:
            if email not in user_status:
                yield {
                    "data": "User not found",
                    "event": "error",
                }
                break
            stats = user_status[email]
            yield {
                "data": {
                    "online": stats["online"],
                    "last_seen": stats["last_seen"].isoformat() if stats["last_seen"] else None,
                },
                "event": "status_update",
            }
            await asyncio.sleep(5)  # Send an update every 5 seconds

    return EventSourceResponse(event_generator())


@app.post("/logout/{email}")
async def logout_user(email: EmailStr):
    """API to update a user's last seen time on logout."""
    if email in user_status:
        user_status[email]["online"] = False
        user_status[email]["last_seen"] = datetime.now()
        logging.debug(f"Updated user {email} last seen time: {user_status[email]['last_seen']}")
        return {"detail": "Successfully logged out"}
    else:
        raise HTTPException(status_code=404, detail="User not found")


@app.get("/messages/{chatId}/{sender_email}")
async def messages(chatId: EmailStr, sender_email: EmailStr, current_user: User = Depends(get_current_user)):
    return await get_messages(chatId, sender_email, current_user)


# @app.get("/users", response_model=List[UserResponse])
# async def get_users(current_user: User = Depends(get_current_user)):
#     users = await user_collection.find({}).to_list(length=None)
#     if "_id" in users:
#         users["_id"] = str(users["_id"])
#     return [serialize_user(user) for user in users]

@app.get("/users/{email}", response_model=List[UserResponse])


async def get_users(email: EmailStr):
    # Fetch the user with the specified email
    user = await user_collection.find_one({"email": email})
    if not user:
        return []  # Return an empty list if the user is not found

    # Convert the "_id" field to a string for the found user
    user["_id"] = str(user["_id"])

    # Fetch all users from the collection
    additional_chat_users = await user_collection.find({}).to_list(length=None)

    # Filter and serialize users whose email matches any chats in the user's "chats"
    return [
        serialize_user(chat_user)
        for chat_user in additional_chat_users
        if any(chat in chat_user['email'] for chat in user.get('chats', []))
    ]


@app.post("/chats/{email}/join")
async def join_chat(email: EmailStr, chat_data: dict, current_user: User = Depends(get_current_user)):
    logging.debug(f"Sender: {email}, Chat Data: {chat_data}")
    print(f"Sender: {email}, Chat Data: {chat_data}")
    try:
        chat_id = chat_data.get("chatId")
        if not chat_id:
            raise HTTPException(status_code=400, detail="Chat ID is required")
        user_check = await user_collection.find({"email": chat_id}).to_list(length=None)
        if not user_check:
            return []

        result = await user_collection.update_one(
            {"email": email},
            {"$addToSet": {"chats": chat_id}}
        )
        if result.modified_count == 0:
            return {"detail": "User not found or already in chat"}
        return {"detail": "Chat joined successfully"}
    except Exception as e:
        logging.error(f"Error joining chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
