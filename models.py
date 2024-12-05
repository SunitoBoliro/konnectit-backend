from typing import List

from pydantic import BaseModel, EmailStr, Field
from bson import ObjectId


class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)

    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(type="string")


class User(BaseModel):
    # id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    username: str
    email: EmailStr
    hashed_password: str
    chats: List[PyObjectId] = []  # List of chat IDs
    pp: str


    class Config:
        json_encoders = {ObjectId: str}


class ChangePPRequest(BaseModel):
    pp: str
    email: EmailStr
    token: str

# class DeleteChatModel(BaseModel):
#     email: EmailStr
#     status: bool



class Message(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    chatId: PyObjectId
    content: str
    timestamp: str
    sender: PyObjectId
    user_id: PyObjectId

    class Config:
        json_encoders = {ObjectId: str}