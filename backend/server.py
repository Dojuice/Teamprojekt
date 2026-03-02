from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from sqlalchemy.orm import Session
from sqlalchemy import desc
import os
import uuid
import json
import shutil
from pathlib import Path
from typing import Optional, List
from pydantic import BaseModel

from database import engine, get_db, Base
from models import Chat, Message
from ocr_service import extract_text_from_pdf
from evaluation_service import evaluate_exam, format_evaluation_as_text
from pdf_report import generate_evaluation_pdf, generate_batch_zip

# Upload directory for temporary file storage
UPLOAD_DIR = Path("/app/uploads") if os.path.exists("/app") else Path("./uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {".pdf"}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB per file

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

class FileUploadResult(BaseModel):
    filename: str
    stored_as: str
    file_type: str  # 'exam' or 'solution'
    size: int
    status: str

class BatchUploadResponse(BaseModel):
    uploaded: List[FileUploadResult]
    errors: List[str]
    total_files: int
    successful: int


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


# --- File Upload ---

def validate_pdf(file: UploadFile) -> Optional[str]:
    """Validate that a file is a PDF. Returns error message or None."""
    if not file.filename:
        return "Datei hat keinen Dateinamen"
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return f"Nur PDF-Dateien erlaubt (erhalten: {ext or 'unbekannt'})"
    if file.content_type and file.content_type not in ("application/pdf", "application/octet-stream"):
        return f"Ungültiger Dateityp: {file.content_type}"
    return None


async def save_upload(file: UploadFile, chat_id: int, file_type: str) -> FileUploadResult:
    """Save an uploaded file to the temp directory."""
    chat_dir = UPLOAD_DIR / str(chat_id) / file_type
    chat_dir.mkdir(parents=True, exist_ok=True)

    # Generate unique filename to avoid collisions
    # Strip any directory components from the filename (e.g. folder uploads)
    unique_id = uuid.uuid4().hex[:8]
    base_name = os.path.basename(file.filename or "unknown.pdf")
    safe_name = f"{unique_id}_{base_name}"
    file_path = chat_dir / safe_name

    # Write file to disk
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail=f"Datei zu groß: {file.filename} ({len(content) // (1024*1024)} MB, max {MAX_FILE_SIZE // (1024*1024)} MB)")

    with open(file_path, "wb") as f:
        f.write(content)

    return FileUploadResult(
        filename=file.filename or "unknown",
        stored_as=safe_name,
        file_type=file_type,
        size=len(content),
        status="uploaded",
    )


@app.post("/api/chats/{chat_id}/upload", response_model=BatchUploadResponse)
async def upload_files(
    chat_id: int,
    files: List[UploadFile] = File(...),
    file_type: str = Query(default="exam"),
    db: Session = Depends(get_db),
):
    """Upload one or more PDF files for a chat.
    file_type: 'exam' or 'solution'
    """
    # Validate chat exists
    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    if file_type not in ("exam", "solution"):
        raise HTTPException(status_code=400, detail="file_type must be 'exam' or 'solution'")

    uploaded: List[FileUploadResult] = []
    errors: List[str] = []

    for file in files:
        # Validate
        error = validate_pdf(file)
        if error:
            errors.append(f"{file.filename}: {error}")
            continue

        try:
            result = await save_upload(file, chat_id, file_type)
            uploaded.append(result)
        except HTTPException as e:
            errors.append(f"{file.filename}: {e.detail}")
        except Exception as e:
            errors.append(f"{file.filename}: Upload fehlgeschlagen ({str(e)})")

    return BatchUploadResponse(
        uploaded=uploaded,
        errors=errors,
        total_files=len(files),
        successful=len(uploaded),
    )


@app.get("/api/chats/{chat_id}/files")
def list_chat_files(chat_id: int, db: Session = Depends(get_db)):
    """List all uploaded files for a chat."""
    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    chat_dir = UPLOAD_DIR / str(chat_id)
    result = {"exam": [], "solution": []}

    for file_type in ["exam", "solution"]:
        type_dir = chat_dir / file_type
        if type_dir.exists():
            for f in type_dir.iterdir():
                if f.is_file():
                    result[file_type].append({
                        "filename": "_".join(f.name.split("_")[1:]),  # Remove UUID prefix
                        "stored_as": f.name,
                        "size": f.stat().st_size,
                    })

    return result


@app.post("/api/chats/{chat_id}/evaluate")
async def evaluate_chat_exams(
    chat_id: int,
    additional_instructions: str = Query(default=""),
    model: str = Query(default="google/gemini-3-flash-preview"),
    db: Session = Depends(get_db),
):
    """Evaluate all uploaded exams against the uploaded solution(s).

    1. Extract text from solution PDFs (OCR if needed)
    2. Extract text from each exam PDF (OCR if needed)
    3. Evaluate each exam against the solution
    4. Return structured results
    """
    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    chat_dir = UPLOAD_DIR / str(chat_id)
    exam_dir = chat_dir / "exam"
    solution_dir = chat_dir / "solution"

    # Check that files exist
    if not exam_dir.exists() or not list(exam_dir.iterdir()):
        raise HTTPException(status_code=400, detail="Keine Klausuren hochgeladen. Bitte laden Sie zuerst Klausur-PDFs hoch.")

    if not solution_dir.exists() or not list(solution_dir.iterdir()):
        raise HTTPException(status_code=400, detail="Keine Musterlösung hochgeladen. Bitte laden Sie zuerst eine Musterlösung hoch.")

    # Step 1: Extract text from solution(s)
    solution_texts: List[str] = []
    for sol_file in sorted(solution_dir.iterdir()):
        if sol_file.is_file() and sol_file.suffix.lower() == ".pdf":
            try:
                result = await extract_text_from_pdf(str(sol_file), context="solution", model=model)
                solution_texts.append(result["text"])
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Fehler beim Lesen der Musterlösung {sol_file.name}: {str(e)}")

    if not solution_texts:
        raise HTTPException(status_code=400, detail="Keine gültige Musterlösung gefunden.")

    combined_solution = "\n\n---\n\n".join(solution_texts)

    # Step 2 & 3: Extract text from each exam and evaluate
    results = []
    exam_files = sorted([f for f in exam_dir.iterdir() if f.is_file() and f.suffix.lower() == ".pdf"])

    for i, exam_file in enumerate(exam_files):
        original_name = "_".join(exam_file.name.split("_")[1:])  # Remove UUID prefix

        try:
            # OCR the exam – tries free local extraction first, Vision API only as fallback
            ocr_result = await extract_text_from_pdf(str(exam_file), context="exam", force_vision=False, model=model)
            exam_text = ocr_result["text"]

            # Evaluate
            evaluation = await evaluate_exam(
                exam_text=exam_text,
                solution_text=combined_solution,
                additional_instructions=additional_instructions,
                model=model,
            )

            results.append({
                "filename": original_name,
                "ocr_method": ocr_result["method"],
                "page_count": ocr_result["page_count"],
                "evaluation": evaluation,
                "formatted_text": format_evaluation_as_text(evaluation),
                "status": "success",
            })

        except Exception as e:
            results.append({
                "filename": original_name,
                "status": "error",
                "error": str(e),
                "formatted_text": f"❌ Fehler bei der Bewertung von {original_name}: {str(e)}",
            })

    # Save results for later PDF download
    _save_evaluation_results(chat_id, results)

    return {
        "chat_id": chat_id,
        "total_exams": len(exam_files),
        "successful": sum(1 for r in results if r["status"] == "success"),
        "results": results,
    }


# --- Download Endpoints ---

def _save_evaluation_results(chat_id: int, results: list):
    """Save evaluation results to a JSON file for later PDF generation."""
    results_dir = UPLOAD_DIR / str(chat_id) / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    results_file = results_dir / "evaluation_results.json"
    with open(results_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)


def _load_evaluation_results(chat_id: int) -> list:
    """Load saved evaluation results."""
    results_file = UPLOAD_DIR / str(chat_id) / "results" / "evaluation_results.json"
    if not results_file.exists():
        return []
    with open(results_file, "r", encoding="utf-8") as f:
        return json.load(f)


@app.get("/api/chats/{chat_id}/download/{exam_index}")
def download_single_report(
    chat_id: int,
    exam_index: int,
    db: Session = Depends(get_db),
):
    """Download a PDF report for a single evaluated exam."""
    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    results = _load_evaluation_results(chat_id)
    if not results:
        raise HTTPException(status_code=404, detail="Keine Bewertungsergebnisse vorhanden. Bitte zuerst eine Bewertung durchführen.")

    if exam_index < 0 or exam_index >= len(results):
        raise HTTPException(status_code=404, detail=f"Klausur-Index {exam_index} nicht gefunden.")

    item = results[exam_index]
    if item.get("status") != "success":
        raise HTTPException(status_code=400, detail=f"Bewertung für diese Klausur war fehlerhaft.")

    filename = item.get("filename", "unknown.pdf")
    evaluation = item.get("evaluation", {})
    pdf_bytes = generate_evaluation_pdf(evaluation, filename=filename)

    report_name = f"Bewertung_{os.path.splitext(filename)[0]}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{report_name}"'},
    )


@app.get("/api/chats/{chat_id}/download-all")
def download_all_reports(
    chat_id: int,
    db: Session = Depends(get_db),
):
    """Download a ZIP file with PDF reports for all evaluated exams."""
    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    results = _load_evaluation_results(chat_id)
    if not results:
        raise HTTPException(status_code=404, detail="Keine Bewertungsergebnisse vorhanden.")

    successful = [r for r in results if r.get("status") == "success"]
    if not successful:
        raise HTTPException(status_code=400, detail="Keine erfolgreichen Bewertungen zum Herunterladen.")

    zip_bytes = generate_batch_zip(successful)
    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="AutoExam_Bewertungen.zip"'},
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
