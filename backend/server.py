from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response, StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc
import os
import uuid
import json
import shutil
import hashlib
import re
from pathlib import Path
from typing import Optional, List, Dict, Any
from pydantic import BaseModel

from database import engine, get_db, Base
from models import Chat, Message
from ocr_service import extract_text_from_pdf
from evaluation_service import evaluate_exam, format_evaluation_as_text, build_solution_rubric
from pdf_report import generate_evaluation_pdf, generate_batch_zip

# Upload directory for temporary file storage
UPLOAD_DIR = Path("/app/uploads") if os.path.exists("/app") else Path("./uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {".pdf"}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB per file
SOLUTION_CACHE_DIR = UPLOAD_DIR / ".cache" / "solutions"
SOLUTION_CACHE_DIR.mkdir(parents=True, exist_ok=True)

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


def _sanitize_error_message(error: Any, max_len: int = 320) -> str:
    """Reduce provider/HTML errors to concise user-safe messages."""
    raw = str(error or "").strip()
    lowered = raw.lower()

    if "<!doctype html" in lowered or "<html" in lowered:
        if "502" in lowered and "bad gateway" in lowered:
            return "Provider-Fehler (502 Bad Gateway) bei OpenRouter. Bitte in 1-2 Minuten erneut versuchen."
        return "Provider lieferte eine HTML-Fehlerseite statt API-Antwort."

    compact = re.sub(r"\s+", " ", raw)
    if len(compact) > max_len:
        return compact[:max_len] + "..."
    return compact


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
        "message": "Hallo! 👋\n\nIch bin AutoExam, Ihr KI-gestützter Klausur-Korrektur-Assistent. Ich helfe Ihnen dabei, handschriftliche Klausuren automatisch zu bewerten.\n\nSo starten Sie:\n📄 Nutzen Sie den Klausur-Button (links) in der Eingabeleiste, um Klausuren oder einen Ordner mit mehreren Klausuren hochzuladen.\n✅ Nutzen Sie den Musterlösungs-Button (daneben), um die Musterlösung des Professors hochzuladen.\n\nSobald beides hochgeladen ist, senden Sie eine Nachricht und ich beginne mit der Bewertung!"
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

    # Clear previous files of this type so only the current prompt's files are used
    type_dir = UPLOAD_DIR / str(chat_id) / file_type
    if type_dir.exists():
        shutil.rmtree(type_dir)
    type_dir.mkdir(parents=True, exist_ok=True)

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
    model: str = Query(default="openai/gpt-5.3-codex"),
    ocr_model: Optional[str] = Query(default=None),
    eval_model: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
):
    """Evaluate uploaded exams against uploaded solution(s) with streaming progress.

    Returns NDJSON (newline-delimited JSON) with progress events and final results.
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

    exam_files = sorted([f for f in exam_dir.iterdir() if f.is_file() and f.suffix.lower() == ".pdf"])
    solution_files = sorted([f for f in solution_dir.iterdir() if f.is_file() and f.suffix.lower() == ".pdf"])
    total_exams = len(exam_files)
    resolved_eval_model = eval_model or model
    resolved_ocr_model = ocr_model or os.getenv("OCR_MODEL", "openai/gpt-4o-mini")

    async def generate():
        # Step 1: Extract text from solution(s)
        print(f"\n{'='*70}")
        print(f"  BEWERTUNG GESTARTET – Chat {chat_id}")
        print(f"  {total_exams} Klausur(en), {len(solution_files)} Musterlösung(en)")
        print(f"  Bewertungsmodell: {resolved_eval_model}")
        print(f"  OCR-Modell: {resolved_ocr_model}")
        print(f"  Extraktions-Methode: AI Vision OCR")
        print(f"{'='*70}")

        yield json.dumps({"type": "progress", "step": "ocr_solution", "label": "Musterlösung wird eingelesen...", "current": 0, "total": total_exams}) + "\n"

        print(f"\n[1/3] MUSTERLÖSUNG EINLESEN")
        solution_texts: List[str] = []
        solution_rubrics: List[Dict[str, Any]] = []
        for sol_idx, sol_file in enumerate(solution_files, 1):
            sol_name = "_".join(sol_file.name.split("_")[1:])
            print(f"  → Musterlösung ({sol_idx}/{len(solution_files)}): {sol_name}")
            try:
                file_hash = hashlib.sha256(sol_file.read_bytes()).hexdigest()
                model_slug = re.sub(r"[^a-zA-Z0-9_.-]", "_", resolved_ocr_model)
                cache_file = SOLUTION_CACHE_DIR / f"{file_hash}_{model_slug}.json"

                if cache_file.exists():
                    cached = json.loads(cache_file.read_text(encoding="utf-8"))
                    solution_text = cached.get("text", "")
                    rubric = cached.get("rubric", {})
                    method = cached.get("method", "cache")
                    print(f"    ✓ Cache-Treffer ({method}, {len(solution_text)} Zeichen)")
                else:
                    result = await extract_text_from_pdf(str(sol_file), context="solution", model=resolved_ocr_model)
                    solution_text = result["text"]
                    rubric = await build_solution_rubric(solution_text, model=resolved_eval_model)

                    payload = {
                        "filename": sol_name,
                        "hash": file_hash,
                        "ocr_model": resolved_ocr_model,
                        "eval_model": resolved_eval_model,
                        "method": result.get("method", "unknown"),
                        "text": solution_text,
                        "rubric": rubric,
                    }
                    cache_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
                    print(f"    ✓ Extrahiert ({result['method']}, {result['page_count']} Seiten, {len(solution_text)} Zeichen)")

                if solution_text.strip():
                    solution_texts.append(solution_text)
                if isinstance(rubric, dict) and rubric.get("tasks"):
                    solution_rubrics.append(rubric)
            except Exception as e:
                display_error = _sanitize_error_message(e)
                print(f"    ✗ FEHLER: {display_error}")
                yield json.dumps({"type": "error", "message": f"Fehler beim Lesen der Musterlösung {sol_file.name}: {display_error}"}) + "\n"
                return

        if not solution_texts:
            print(f"  ✗ Keine gültige Musterlösung gefunden!")
            yield json.dumps({"type": "error", "message": "Keine gültige Musterlösung gefunden."}) + "\n"
            return

        combined_solution = "\n\n---\n\n".join(solution_texts)

        merged_rubric: Dict[str, Any] = {"tasks": [], "total_points": 0, "notes": "Zusammengeführt"}
        seen_task_numbers = set()
        for rubric in solution_rubrics:
            for task in rubric.get("tasks", []):
                task_num = str(task.get("task_number", "")).strip()
                if task_num and task_num not in seen_task_numbers:
                    merged_rubric["tasks"].append(task)
                    seen_task_numbers.add(task_num)
        merged_rubric["total_points"] = sum(int((t.get("points_max", 0) or 0)) for t in merged_rubric["tasks"])

        print(f"  ✓ Musterlösung bereit ({len(combined_solution)} Zeichen)")
        print(f"  ✓ Bewertungsraster: {len(merged_rubric['tasks'])} Aufgaben")

        # Step 2: Extract text from each exam + Step 3: Evaluate each exam
        print(f"\n[2/3] TEXT EXTRAHIEREN & [3/3] KORREKTUR")
        results = []
        for i, exam_file in enumerate(exam_files):
            original_name = "_".join(exam_file.name.split("_")[1:])

            # --- OCR Progress ---
            print(f"\n  ── Klausur ({i+1}/{total_exams}): {original_name} ──")
            print(f"  [OCR] Extrahiere Text...")
            yield json.dumps({"type": "progress", "step": "ocr", "label": f"Text wird extrahiert: {original_name}", "current": i + 1, "total": total_exams}) + "\n"

            try:
                ocr_result = await extract_text_from_pdf(str(exam_file), context="exam", model=resolved_ocr_model)
                exam_text = ocr_result["text"]

                print(f"  [OCR] ✓ Methode: {ocr_result['method']}, Seiten: {ocr_result['page_count']}, Zeichen: {len(exam_text)}")

                # --- Show extracted text per exercise ---
                print(f"  [OCR] Extrahierter Text:")
                print(f"  {'─'*60}")
                for line in exam_text.split('\n'):
                    print(f"  │ {line}")
                print(f"  {'─'*60}")

                # --- Evaluation Progress ---
                print(f"  [EVAL] Korrektur via API ({resolved_eval_model})...")
                yield json.dumps({"type": "progress", "step": "eval", "label": f"Klausur wird korrigiert: {original_name}", "current": i + 1, "total": total_exams}) + "\n"

                evaluation = await evaluate_exam(
                    exam_text=exam_text,
                    solution_text=combined_solution,
                    solution_rubric=merged_rubric,
                    additional_instructions=additional_instructions,
                    model=resolved_eval_model,
                )

                # --- Show evaluation result ---
                student_name = evaluation.get("student_name", "Unbekannt")
                overall_grade = evaluation.get("overall_grade", "–")
                overall_score = evaluation.get("overall_score", 0)
                total_pts = evaluation.get("total_points", "–")
                max_pts = evaluation.get("max_points", "–")
                print(f"  [EVAL] ✓ Ergebnis: {student_name} → Note {overall_grade} ({overall_score}%, {total_pts}/{max_pts} Punkte)")
                for task in evaluation.get("tasks", []):
                    t_num = task.get("task_number", "?")
                    t_pts = task.get("points_achieved", "?")
                    t_max = task.get("points_max", "?")
                    t_status = task.get("status", "?")
                    print(f"       Aufgabe {t_num}: {t_pts}/{t_max} Pkt. ({t_status})")

                results.append({
                    "filename": original_name,
                    "ocr_method": ocr_result["method"],
                    "page_count": ocr_result["page_count"],
                    "evaluation": evaluation,
                    "formatted_text": format_evaluation_as_text(evaluation),
                    "status": "success",
                })

            except Exception as e:
                display_error = _sanitize_error_message(e)
                print(f"  ✗ FEHLER bei {original_name}: {display_error}")
                results.append({
                    "filename": original_name,
                    "status": "error",
                    "error": display_error,
                    "formatted_text": f"Fehler bei der Bewertung von {original_name}: {display_error}",
                })

        # Step 4: Generate summary
        successful_count = sum(1 for r in results if r["status"] == "success")
        print(f"\n  ── Zusammenfassung ──")
        print(f"  {successful_count}/{total_exams} Klausuren erfolgreich bewertet")
        yield json.dumps({"type": "progress", "step": "summary", "label": "Zusammenfassung wird erstellt...", "current": total_exams, "total": total_exams}) + "\n"

        # Save results for later PDF download
        _save_evaluation_results(chat_id, results)

        print(f"\n{'='*70}")
        print(f"  BEWERTUNG ABGESCHLOSSEN – Chat {chat_id}")
        print(f"  {successful_count}/{total_exams} erfolgreich")
        if successful_count > 0:
            avg_score = sum(
                r["evaluation"].get("overall_score", 0) 
                for r in results if r["status"] == "success"
            ) / successful_count
            avg_grade = sum(
                float(r["evaluation"].get("overall_grade", "0").replace(",", "."))
                for r in results if r["status"] == "success"
            ) / successful_count
            print(f"  Durchschnitt: {avg_score:.1f}% (Note {avg_grade:.1f})")
        print(f"{'='*70}\n")

        # Final result
        yield json.dumps({
            "type": "result",
            "chat_id": chat_id,
            "total_exams": total_exams,
            "successful": successful_count,
            "eval_model": resolved_eval_model,
            "ocr_model": resolved_ocr_model,
            "rubric_task_count": len(merged_rubric.get("tasks", [])),
            "results": results,
        }) + "\n"

    return StreamingResponse(generate(), media_type="application/x-ndjson")


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
