import logging

from fastapi import Depends, HTTPException
from pydantic import EmailStr

from db import message_collection, serialize_message
from get_current_user import get_current_user
from models import User


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
