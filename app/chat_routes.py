# app/chat_routes.py

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
import uuid
from datetime import datetime

from . import models, chat_models, chat_schemas, auth, schemas
from .dependencies import get_db
from .logging_service import log_activity
from .media_service import save_media
import traceback

router = APIRouter()

@router.get("/chats", response_model=chat_schemas.ChatListResponse)
def get_chats(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    # Get all chats where the current user is a participant
    chat_participants = db.query(chat_models.ChatParticipant).filter(
        chat_models.ChatParticipant.user_id == current_user.id
    ).all()
    
    chat_list = []
    for participant in chat_participants:
        chat = participant.chat
        
        # Find the other participants
        other_participants = db.query(chat_models.ChatParticipant).filter(
            chat_models.ChatParticipant.chat_id == chat.id,
            chat_models.ChatParticipant.user_id != current_user.id
        ).all()
        
        if not other_participants:
            continue
            
        other_user_id = other_participants[0].user_id
        other_user = db.query(models.User).filter(models.User.id == other_user_id).first()
        
        # Get last message
        last_message = db.query(chat_models.Message).filter(
            chat_models.Message.chat_id == chat.id
        ).order_by(chat_models.Message.timestamp.desc()).first()
        
        # Check if there are unread messages
        unread_messages = db.query(chat_models.Message).filter(
            chat_models.Message.chat_id == chat.id,
            chat_models.Message.sender_id != current_user.id,
            chat_models.Message.read == False
        ).count() > 0
        
        chat_item = chat_schemas.Chat(
            id=chat.id,
            recipient_id=str(other_user.id),
            recipient_name=other_user.name,
            last_message=last_message.content if last_message else None,
            last_message_time=last_message.timestamp if last_message else None,
            unread=unread_messages
        )
        chat_list.append(chat_item)
    
    # Log activity
    log = schemas.ActivityLogCreate(action=f"Retrieved {len(chat_list)} chats")
    log_activity(db, log, current_user.id)
    
    return chat_schemas.ChatListResponse(success=True, data=chat_list)

@router.post("/chats", response_model=chat_schemas.ChatResponse)
def create_chat(request: chat_schemas.CreateChatRequest, 
                db: Session = Depends(get_db), 
                current_user: models.User = Depends(auth.get_current_user)):
    # Find the recipient by username
    recipient = db.query(models.User).filter(models.User.username == request.username).first()
    if not recipient:
        return chat_schemas.ChatResponse(success=False, error="Recipient not found")
    
    # Check if chat already exists between these users
    existing_chat = None
    user_chats = db.query(chat_models.ChatParticipant).filter(
        chat_models.ChatParticipant.user_id == current_user.id
    ).all()
    
    for user_chat in user_chats:
        # Check if the recipient is also in this chat
        recipient_in_chat = db.query(chat_models.ChatParticipant).filter(
            chat_models.ChatParticipant.chat_id == user_chat.chat_id,
            chat_models.ChatParticipant.user_id == recipient.id
        ).first()
        
        if recipient_in_chat:
            existing_chat = user_chat.chat
            break
    
    if existing_chat:
        chat_data = chat_schemas.Chat(
            id=existing_chat.id,
            recipient_id=str(recipient.id),
            recipient_name=recipient.name,
            last_message=None,
            last_message_time=None,
            unread=False
        )
        return chat_schemas.ChatResponse(success=True, data=chat_data)
    
    # Create new chat
    chat_id = str(uuid.uuid4())
    new_chat = chat_models.Chat(id=chat_id)
    db.add(new_chat)
    
    # Add participants
    participant1 = chat_models.ChatParticipant(chat_id=chat_id, user_id=current_user.id)
    participant2 = chat_models.ChatParticipant(chat_id=chat_id, user_id=recipient.id)
    db.add(participant1)
    db.add(participant2)
    
    db.commit()
    
    # Log activity
    log = schemas.ActivityLogCreate(action=f"Created new chat with {recipient.username}")
    log_activity(db, log, current_user.id)
    
    chat_data = chat_schemas.Chat(
        id=chat_id,
        recipient_id=str(recipient.id),
        recipient_name=recipient.name,
        last_message=None,
        last_message_time=None,
        unread=False
    )
    
    return chat_schemas.ChatResponse(success=True, data=chat_data)

@router.get("/chats/{chat_id}/messages", response_model=chat_schemas.MessageListResponse)
def get_messages(chat_id: str, 
                 db: Session = Depends(get_db), 
                 current_user: models.User = Depends(auth.get_current_user)):
    # Verify chat exists and user is a participant
    participant = db.query(chat_models.ChatParticipant).filter(
        chat_models.ChatParticipant.chat_id == chat_id,
        chat_models.ChatParticipant.user_id == current_user.id
    ).first()
    
    if not participant:
        return chat_schemas.MessageListResponse(success=False, error="Chat not found or you're not a participant")
    
    # Get all messages in this chat
    messages = db.query(chat_models.Message).filter(
        chat_models.Message.chat_id == chat_id
    ).order_by(chat_models.Message.timestamp).all()
    
    # Mark messages as read if they were sent by the other user
    unread_messages = db.query(chat_models.Message).filter(
        chat_models.Message.chat_id == chat_id,
        chat_models.Message.sender_id != current_user.id,
        chat_models.Message.read == False
    ).all()
    
    for message in unread_messages:
        message.read = True
    
    db.commit()
    
    # Log activity
    log = schemas.ActivityLogCreate(action=f"Retrieved {len(messages)} messages from chat {chat_id}")
    log_activity(db, log, current_user.id)
    
    message_list = []
    for message in messages:
        sender = db.query(models.User).filter(models.User.id == message.sender_id).first()
        message_item = chat_schemas.Message(
            id=message.id,
            chat_id=message.chat_id,
            sender_id=str(message.sender_id),
            sender_name=sender.name,
            content=message.content,
            message_type=message.message_type,
            media_url=message.media_url,
            timestamp=message.timestamp,
            read=message.read
        )
        message_list.append(message_item)
    
    return chat_schemas.MessageListResponse(success=True, data=message_list)

@router.post("/messages", response_model=chat_schemas.MessageResponse)
def send_message(request: chat_schemas.SendMessageRequest, 
                 db: Session = Depends(get_db), 
                 current_user: models.User = Depends(auth.get_current_user)):
    # Verify chat exists and user is a participant
    participant = db.query(chat_models.ChatParticipant).filter(
        chat_models.ChatParticipant.chat_id == request.chat_id,
        chat_models.ChatParticipant.user_id == current_user.id
    ).first()
    
    if not participant:
        return chat_schemas.MessageResponse(success=False, error="Chat not found or you're not a participant")
    
    # Create new message with optional media
    message_id = str(uuid.uuid4())
    new_message = chat_models.Message(
        id=message_id,
        chat_id=request.chat_id,
        sender_id=current_user.id,
        content=request.content,
        message_type=request.message_type,
        media_url=request.media_url,  # URL media file (optional)
        timestamp=datetime.utcnow(),
        read=False
    )
    
    db.add(new_message)
    db.commit()
    db.refresh(new_message)
    
    # Log activity
    log = schemas.ActivityLogCreate(action=f"Sent {request.message_type} to chat {request.chat_id}")
    log_activity(db, log, current_user.id)
    
    # Construct response
    message_data = chat_schemas.Message(
        id=new_message.id,
        chat_id=new_message.chat_id,
        sender_id=str(current_user.id),
        sender_name=current_user.name,
        content=new_message.content,
        message_type=new_message.message_type,
        media_url=new_message.media_url,
        timestamp=new_message.timestamp,
        read=new_message.read
    )
    
    return chat_schemas.MessageResponse(success=True, data=message_data)

@router.post("/messages/upload-media")
async def upload_media(
    file: UploadFile = File(...), 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    try:
        # Validasi tipe file
        content_type = file.content_type
        
        if content_type.startswith("image/"):
            file_type = "image"
        elif content_type.startswith("video/"):
            file_type = "video"
        else:
            raise HTTPException(status_code=400, detail="Only image and video files are allowed")
        
        # Simpan file
        media_url = await save_media(file)
        
        # Log aktivitas
        log = schemas.ActivityLogCreate(action=f"Uploaded {file_type}")
        log_activity(db, log, current_user.id)
        
        return {
            "success": True, 
            "data": {
                "media_url": media_url,
                "message_type": file_type
            }
        }
    except Exception as e:
        print(f"Error in upload_media: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))