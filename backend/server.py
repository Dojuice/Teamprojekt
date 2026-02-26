from fastapi import FastAPI, File, UploadFile, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc
import os
from typing import Optional, List
from pydantic import BaseModel

from database import engine, get_db, Base
from models import Chat, Message

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="AutoExam API", version="1.0.0")

# CORS middleware to allow frontend to communicate with backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://frontend:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Pydantic schemas ---

class MessageCreate(BaseModel):
    sender: str
    text: str

class MessageOut(BaseModel):
    id: int
    sender: str
    text: str

    class Config:
        from_attributes = True

class ChatOut(BaseModel):
    id: int
    title: str
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True

class ChatDetail(BaseModel):
    id: int
    title: str
    messages: List[MessageOut]

    class Config:
        from_attributes = True

class ChatTitleUpdate(BaseModel):
    title: str


# --- Health / Welcome ---

@app.get("/")
async def root():
    return {"message": "AutoExam API is running", "version": "1.0.0", "status": "healthy"}

@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "service": "backend"}

@app.get("/api/welcome")
async def welcome():
    return {
        "message": "Hello! 👋\n\nI'm AutoExam, your AI-powered exam correction assistant. I help you automatically evaluate handwritten exams.\n\nTo get started:\n📄 Use the exam button (left) in the input bar to upload exams or a folder with multiple exams.\n✅ Use the solution button (right next to it) to upload the professor's solution.\n\nOnce both are uploaded, just send a message and I'll begin the evaluation!"
    }


# --- Chat CRUD ---

@app.post("/api/chats", response_model=ChatOut)
def create_chat(db: Session = Depends(get_db)):
    """Create a new chat session."""
    chat = Chat(title="Neuer Chat")
    db.add(chat)
    db.commit()
    db.refresh(chat)
    return ChatOut(
        id=chat.id,
        title=chat.title,
        created_at=chat.created_at.isoformat(),
        updated_at=chat.updated_at.isoformat(),
    )

@app.get("/api/chats", response_model=List[ChatOut])
def list_chats(db: Session = Depends(get_db)):
    """List all chats, newest first."""
    chats = db.query(Chat).order_by(desc(Chat.updated_at)).all()
    return [
        ChatOut(
            id=c.id,
            title=c.title,
            created_at=c.created_at.isoformat(),
            updated_at=c.updated_at.isoformat(),
        )
        for c in chats
    ]

@app.get("/api/chats/{chat_id}", response_model=ChatDetail)
def get_chat(chat_id: int, db: Session = Depends(get_db)):
    """Get a chat with all its messages."""
    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    return ChatDetail(
        id=chat.id,
        title=chat.title,
        messages=[MessageOut(id=m.id, sender=m.sender, text=m.text) for m in chat.messages],
    )

@app.patch("/api/chats/{chat_id}", response_model=ChatOut)
def update_chat_title(chat_id: int, body: ChatTitleUpdate, db: Session = Depends(get_db)):
    """Update a chat's title."""
    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    chat.title = body.title
    db.commit()
    db.refresh(chat)
    return ChatOut(
        id=chat.id,
        title=chat.title,
        created_at=chat.created_at.isoformat(),
        updated_at=chat.updated_at.isoformat(),
    )

@app.delete("/api/chats/{chat_id}")
def delete_chat(chat_id: int, db: Session = Depends(get_db)):
    """Delete a chat and all its messages."""
    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    db.delete(chat)
    db.commit()
    return {"detail": "Chat deleted"}


# --- Messages ---

@app.post("/api/chats/{chat_id}/messages", response_model=MessageOut)
def add_message(chat_id: int, body: MessageCreate, db: Session = Depends(get_db)):
    """Add a message to a chat."""
    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    msg = Message(chat_id=chat_id, sender=body.sender, text=body.text)
    db.add(msg)
    # Auto-title: use the first user message as chat title
    if body.sender == "user" and chat.title == "Neuer Chat":
        chat.title = body.text[:60] + ("..." if len(body.text) > 60 else "")
    db.commit()
    db.refresh(msg)
    return MessageOut(id=msg.id, sender=msg.sender, text=msg.text)


# --- Legacy upload/evaluate ---

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    if not file:
        raise HTTPException(status_code=400, detail="No file provided")
    return {"message": "File uploaded successfully", "filename": file.filename, "content_type": file.content_type, "status": "processing"}

@app.post("/api/evaluate")
async def evaluate_exam(data: dict):
    return {"message": "Evaluation endpoint - to be implemented", "data": data}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
