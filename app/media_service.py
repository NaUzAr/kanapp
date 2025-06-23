# app/media_service.py

import os
import uuid
from fastapi import UploadFile, HTTPException
import aiofiles
import shutil

UPLOAD_DIR = "uploads"
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

async def save_media(file: UploadFile) -> str:
    try:
        # Validate file size
        file.file.seek(0, 2)  # Go to the end of the file
        size = file.file.tell()  # Get current position (size)
        file.file.seek(0)  # Go back to the start
        
        if size > MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail=f"File size exceeds the limit of {MAX_FILE_SIZE/1024/1024}MB")
        
        # Validate content type
        content_type = file.content_type
        if content_type.startswith("image/"):
            file_type = "image"
            ext = content_type.split("/")[1]
        elif content_type.startswith("video/"):
            file_type = "video"
            ext = content_type.split("/")[1]
        elif content_type.startswith("audio/"):
            file_type = "audio"
            ext = content_type.split("/")[1] if "/" in content_type else "mp4"
        else:
            raise HTTPException(status_code=400, detail="Unsupported file type")
        
        # Create unique filename
        filename = f"{file_type}_{uuid.uuid4()}.{ext}"
        filepath = os.path.join(UPLOAD_DIR, filename)
        
        # Ensure upload directory exists
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        
        # Save file
        with open(filepath, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Return the file path relative to the media endpoint
        return filename
    except Exception as e:
        print(f"Error saving media: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error saving file: {str(e)}")