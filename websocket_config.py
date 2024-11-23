import json
import logging
from datetime import datetime
from typing import Dict

from jose import jwt, JWTError
from pydantic import EmailStr
from starlette.websockets import WebSocket, WebSocketDisconnect

from auth import SECRET_KEY, ALGORITHM
from db import message_collection

# Dictionary to store active WebSocket connections and user status
active_connections: Dict[EmailStr, WebSocket] = {}
user_status: Dict[EmailStr, dict] = {}  # Tracks online status and last seen time

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
        user_status[current_user_email] = {"online": True, "last_seen": None}
        print(f"{current_user_email} is now online")

        try:
            while True:
                # Receive messages and update activity timestamp
                data = await websocket.receive_text()
                message = json.loads(data)
                message["sender"] = current_user_email
                await message_collection.insert_one(message)
                await broadcast(message)

                # Update user activity
                user_status[current_user_email] = {
                    "online": True,
                    "last_seen": datetime.utcnow(),
                }
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
