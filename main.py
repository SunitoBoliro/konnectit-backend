# main.py
import asyncio
from datetime import timedelta, datetime
from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect, Depends
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import EmailStr
from sse_starlette import EventSourceResponse
from starlette import status
from models import User, Message
from db import user_collection, message_collection, serialize_user, serialize_message, seed_users
from auth import create_access_token, validate_token, SECRET_KEY, ALGORITHM
from bson import ObjectId
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Optional
import json
import logging
from schemas import UserCreate, UserLogin, UserResponse, MessageCreate, MessageResponse, PyObjectId
from utils import hash_password, verify_password

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


async def get_current_user(token: str = Query(...)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        user = await user_collection.find_one({"email": email})
        if user is None:
            raise credentials_exception
        return user
    except JWTError:
        raise credentials_exception


@app.post("/register", response_model=UserResponse)
async def register_user(user: UserCreate):
    existing_user = await user_collection.find_one({"email": user.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_password = hash_password(user.password)
    new_user = User(username=user.username, email=user.email, hashed_password=hashed_password, chats=[])
    result = await user_collection.insert_one(new_user.dict())
    user_data = serialize_user({**new_user.dict(), "_id": result.inserted_id})

    # Notify connected WebSocket clients about the new user
    for client in connected_clients:
        await client.send_json({"event": "new_user", "data": user_data})

    return user_data



@app.post("/login")
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


@app.get("/validate")
async def validate_token_endpoint(token: str = Query(...)):
    try:
        # Decode the token using the secret key and algorithm
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        logging.debug(f"Token payload: {payload}")
        return {"isValid": True}  # If no exception is raised, the token is valid
    except JWTError:
        logging.error("Invalid token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )


# Dictionary to store active WebSocket connections and user status
active_connections: Dict[EmailStr, WebSocket] = {}
user_status: Dict[EmailStr, dict] = {}  # Tracks online status and last seen time


@app.websocket("/ws/{token}")
async def websocket_endpoint(websocket: WebSocket, token: str):
    try:
        # Decode the token to get the current user
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        current_user_email = payload.get("sub")
        if not current_user_email:
            await websocket.close(code=1008, reason="Invalid token")
            return

        # Accept the WebSocket connection
        await websocket.accept()
        active_connections[current_user_email] = websocket
        logging.info(f"User {current_user_email} connected. Active connections: {list(active_connections.keys())}")

        # Mark user as online and update status
        # user_status[current_user_email] = {"online": True, "last_seen": None}
        # print(f"{current_user_email} is now online")

        try:
            while True:
                # Receive messages and update activity timestamp
                data = await websocket.receive_text()
                message = json.loads(data)
                message["sender"] = current_user_email
                await message_collection.insert_one(message)
                await broadcast(message)

                # Update user activity
                # user_status[current_user_email] = {
                #     "online": True,
                #     "last_seen": datetime.utcnow(),
                # }
        except WebSocketDisconnect:
            logging.info(f"User {current_user_email} disconnected.")
        finally:
            # Handle disconnection: mark user as offline
            active_connections.pop(current_user_email, None)
            logging.info(
                f"User {current_user_email} disconnected. Active connections: {list(active_connections.keys())}")

            user_status[current_user_email] = {
                "online": False,
                "last_seen": datetime.utcnow(),
            }
            print(f"{current_user_email} went offline at {user_status[current_user_email]['last_seen']}")
    except JWTError as e:
        await websocket.close(code=1008, reason="Invalid token")
        logging.error(f"JWTError: {e}")
    except Exception as e:
        await websocket.close(code=1011, reason="Internal server error")
        logging.error(f"WebSocket Error: {e}")


async def broadcast(message: dict):
    """
    This function broadcasts the message to both users in the chat.
    The message chatId is now the email of the recipient, so we need to handle both users involved.
    """
    chat_id = message.get("chatId")
    if not chat_id:
        logging.warning("Message without chatId received. Skipping broadcast.")
        return

    # Assuming `chatId` corresponds to the recipient's email. Get both participants:
    user_emails = [message["sender"], chat_id]  # Both sender and recipient need to receive the message

    # Debugging Logs
    logging.debug(f"Broadcasting message to users: {user_emails}")

    if "_id" in message:
        message["_id"] = str(message["_id"])

    # Send message to each user connected
    for user_email in user_emails:
        if user_email in active_connections:
            try:
                # Send the message to the user
                await active_connections[user_email].send_text(json.dumps(message))
                logging.info(f"Message sent to {user_email}")
            except Exception as e:
                # Error handling for failed message delivery
                logging.error(f"Error sending message to {user_email}: {e}")
                # Clean up broken connections
                active_connections.pop(user_email, None)


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
async def get_messages(chatId: EmailStr, sender_email: EmailStr, current_user: User = Depends(get_current_user)):
    try:
        logging.info(f"Fetching messages for chatId={chatId} and sender_email={sender_email}")
        messages = await message_collection.find({
            "$or": [
                {"chatId": chatId, "sender": sender_email},
                {"chatId": sender_email, "sender": chatId}
            ]
        }).to_list(length=None)
        serialized_messages = [serialize_message(msg) for msg in messages]
        logging.debug(f"Fetched messages: {serialized_messages}")
        return serialized_messages
    except Exception as e:
        logging.error(f"Error fetching messages: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching messages: {e}")


@app.get("/users", response_model=List[UserResponse])
async def get_users(current_user: User = Depends(get_current_user)):
    users = await user_collection.find({}).to_list(length=None)
    if "_id" in users:
        users["_id"] = str(users["_id"])
    return [serialize_user(user) for user in users]


@app.post("/chats/{email}/join")
async def join_chat(email: EmailStr, chat_data: dict, current_user: User = Depends(get_current_user)):
    logging.debug(f"Sender: {email}, Chat Data: {chat_data}")
    print(f"Sender: {email}, Chat Data: {chat_data}")
    try:
        chat_id = chat_data.get("chatId")
        if not chat_id:
            raise HTTPException(status_code=400, detail="Chat ID is required")

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
