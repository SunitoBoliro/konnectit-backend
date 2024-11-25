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


class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    pp: str



class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    # id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    id: str
    username: str
    email: EmailStr

    class Config:
        json_encoders = {ObjectId: str}


class MessageCreate(BaseModel):
    type: str
    chatId: int
    content: str
    timestamp: str
    sender: str
    user_id: PyObjectId

    class Config:
        json_encoders = {ObjectId: str}


class MessageResponse(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    chatId: EmailStr
    content: str
    timestamp: str
    sender: str
    # user_id: PyObjectId

    class Config:
        json_encoders = {ObjectId: str}
