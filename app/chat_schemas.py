# app/chat_schemas.py

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

# Message schemas
class MessageBase(BaseModel):
    content: str

class SendMessageRequest(MessageBase):
    chat_id: str
    message_type: str = "text"
    media_url: Optional[str] = None

class Message(BaseModel):
    id: str
    chat_id: str
    sender_id: str
    sender_name: str
    content: str
    message_type: str = "text"
    media_url: Optional[str] = None
    timestamp: datetime
    read: bool

    class Config:
        from_attributes = True

# Chat schemas
class CreateChatRequest(BaseModel):
    username: str = Field(..., description="Username of the recipient")

class Chat(BaseModel):
    id: str
    recipient_id: str
    recipient_name: str
    last_message: Optional[str] = None
    last_message_time: Optional[datetime] = None
    unread: bool = False

    class Config:
        from_attributes = True

# Response models
class MessageResponse(BaseModel):
    success: bool
    data: Optional[Message] = None
    error: Optional[str] = None

class ChatResponse(BaseModel):
    success: bool
    data: Optional[Chat] = None
    error: Optional[str] = None

class ChatListResponse(BaseModel):
    success: bool
    data: Optional[List[Chat]] = None
    error: Optional[str] = None

class MessageListResponse(BaseModel):
    success: bool
    data: Optional[List[Message]] = None
    error: Optional[str] = None