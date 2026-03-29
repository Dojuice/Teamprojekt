"""
OCR Service – PDF to text extraction using PyMuPDF + OpenRouter Vision.

Flow:
1. PDF → Images (via PyMuPDF/fitz)
2. Images → Text (via OpenRouter Vision API – AI Vision OCR)
"""

import fitz  # PyMuPDF
import base64
import os
import asyncio
from pathlib import Path
from typing import Any, List, Optional
from openai import OpenAI

_client: Optional[OpenAI] = None


def get_client() -> OpenAI:
    """Get or create the OpenRouter client (OpenAI-compatible)."""
    global _client
    if _client is None:
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise RuntimeError(
                "OPENROUTER_API_KEY environment variable is not set. "
                "Get a free key at https://openrouter.ai/keys"
            )
        _client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
        )
    return _client


def pdf_to_images(pdf_path: str, dpi: int = 200) -> List[bytes]:
    """Convert a PDF file to a list of PNG images (one per page).

    Args:
        pdf_path: Path to the PDF file.
        dpi: Resolution for rendering. 200 is good for OCR.

    Returns:
        List of PNG image bytes.
    """
    images: List[bytes] = []
    doc = fitz.open(pdf_path)

    zoom = dpi / 72  # 72 is the default PDF resolution
    matrix = fitz.Matrix(zoom, zoom)

    for page in doc:
        pix = page.get_pixmap(matrix=matrix)
        img_bytes = pix.tobytes("png")
        images.append(img_bytes)

    doc.close()
    return images


def images_to_base64(images: List[bytes]) -> List[str]:
    """Convert image bytes to base64 strings for the API."""
    return [base64.b64encode(img).decode("utf-8") for img in images]


def save_images_for_debug(images: List[bytes], pdf_path: str, output_dir: str = "debug_images"):
    """Save images to disk for debugging (no API needed).

    Args:
        images: List of PNG image bytes.
        pdf_path: Original PDF path (for naming).
        output_dir: Directory to save images.
    """
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    pdf_name = Path(pdf_path).stem
    for i, img_bytes in enumerate(images, 1):
        img_file = output_path / f"{pdf_name}_page_{i}.png"
        with open(img_file, "wb") as f:
            f.write(img_bytes)
        print(f"[DEBUG] Saved image: {img_file}")

    print(f"[DEBUG] All {len(images)} images saved to {output_path.absolute()}")


async def extract_text_with_vision(images: List[bytes], context: str = "exam", model: str = "google/gemini-2.0-flash-exp:free") -> str:
    """Use AI Vision via OpenRouter to extract text from images (OCR).

    This is especially useful for handwritten content.

    Args:
        images: List of PNG image bytes.
        context: Either 'exam' or 'solution' – adjusts the prompt.
        model: OpenRouter model ID.

    Returns:
        Extracted text from all images.
    """
    math_instructions = (
        "Schreibe alle mathematischen Ausdrücke in LaTeX-Notation (OHNE $-Zeichen oder LaTeX-Umgebungen). "
        "Beispiele: Potenzen als x^2, x^3; Brüche als \\frac{a}{b}; Grenzwerte als \\lim_{x \\to 2}; "
        "Integrale als \\int_0^2; Ableitungen als f'(x), f''(x); Wurzeln als \\sqrt{x}; "
        "Summen als \\sum_{i=1}^{n}; griechische Buchstaben als \\alpha, \\beta etc. "
        "Normaler Text bleibt normaler Text – nur mathematische Symbole und Formeln in LaTeX-Notation."
    )

    if context == "exam":
        system_prompt = (
            "Du bist ein OCR-Spezialist. Extrahiere den gesamten Text aus den folgenden "
            "Klausur-Seiten. Achte besonders auf handschriftliche Antworten. "
            "Gib den Text strukturiert zurück – trenne verschiedene Aufgaben klar voneinander. "
            "Wenn du unsicher bist, markiere die Stelle mit [unleserlich]. "
            "WICHTIG: Extrahiere EXAKT das, was der Student geschrieben hat – Buchstabe für Buchstabe, Zahl für Zahl. "
            "Du darfst NIEMALS interpretieren, was der Student gemeint haben könnte oder was mathematisch korrekt wäre. "
            "Wenn dort eine 3 steht, schreibe eine 3 – auch wenn das Ergebnis dann mathematisch falsch ist. "
            "Wenn dort eine 2 steht, schreibe eine 2. Verändere KEINE Zahlen, Vorzeichen oder Symbole, "
            "um ein 'richtigeres' Ergebnis zu erzeugen. Du bist ein neutraler Textextraktor, KEIN Korrektor. "
            "Deine Aufgabe ist NUR das exakte Ablesen der Handschrift, nicht das Korrigieren oder Interpretieren. "
            f"{math_instructions} "
            "Gib NUR den extrahierten Text zurück, keine Kommentare."
        )
    else:
        system_prompt = (
            "Du bist ein OCR-Spezialist. Extrahiere den gesamten Text aus den folgenden "
            "Musterlösungs-Seiten. Gib den Text strukturiert zurück – trenne verschiedene "
            "Aufgaben und Teilaufgaben klar voneinander. "
            f"{math_instructions} "
            "Gib NUR den extrahierten Text zurück, keine Kommentare."
        )

    client = get_client()

    # Build content with images (OpenAI Vision format – works with OpenRouter)
    content: list = [{"type": "text", "text": f"Bitte extrahiere den Text aus diesen {len(images)} Seiten:"}]
    b64_images = images_to_base64(images)
    for b64 in b64_images:
        content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/png;base64,{b64}",
                "detail": "high",
            },
        })

    last_error = "Leere oder unvollständige OCR-Antwort vom Modell"
    for attempt in range(1, 4):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": content},
                ],
                max_tokens=4096,
                temperature=0.1,
            )

            choices: Any = getattr(response, "choices", None)
            if not choices or len(choices) == 0:
                last_error = "Antwort enthält kein 'choices'-Feld"
                raise ValueError(last_error)

            message = getattr(choices[0], "message", None)
            if not message:
                last_error = "Antwort enthält keine Nachricht"
                raise ValueError(last_error)

            content_text = getattr(message, "content", None)
            if not content_text or not str(content_text).strip():
                last_error = "Antwort enthält keinen OCR-Text"
                raise ValueError(last_error)

            return str(content_text)
        except Exception as exc:
            last_error = str(exc)
            if attempt < 3:
                await asyncio.sleep(0.6 * attempt)

    raise RuntimeError(f"Vision-OCR fehlgeschlagen ({model}): {last_error}")


def extract_text_native(pdf_path: str) -> dict:
    """Try native PDF text extraction for typed PDFs before falling back to Vision OCR."""
    filename = Path(pdf_path).name
    chunks: List[str] = []

    doc = fitz.open(pdf_path)
    try:
        for page in doc:
            page_text = page.get_text("text") or ""
            if page_text.strip():
                chunks.append(page_text.strip())
    finally:
        doc.close()

    text = "\n\n".join(chunks).strip()
    quality = "high" if len(text) >= 600 else "low"
    return {
        "filename": filename,
        "method": "native_pdf_text",
        "text": text,
        "quality": quality,
    }


async def extract_text_from_pdf(pdf_path: str, context: str = "exam", model: str = "openai/gpt-5.3-codex") -> dict:
    """Extract text from a PDF file using AI Vision OCR.

    Args:
        pdf_path: Path to the PDF file.
        context: 'exam' or 'solution'.
        model: OpenRouter model ID.

    Returns:
        Dict with extracted text and metadata.
    """
    filename = Path(pdf_path).name
    result = {
        "filename": filename,
        "method": "vision_ocr",
        "text": "",
        "page_count": 0,
        "quality": "ocr",
    }

    # Get page count
    doc = fitz.open(pdf_path)
    result["page_count"] = len(doc)
    doc.close()

    # Try native extraction first for non-handwritten contexts (typically printed model solutions).
    if context == "solution":
        native = extract_text_native(pdf_path)
        if native["text"] and len(native["text"]) >= 600:
            result["method"] = native["method"]
            result["text"] = native["text"]
            result["quality"] = native["quality"]
            print(f"[OCR] '{filename}': Native PDF text extraction used ({len(result['text'])} chars)")
            return result

    print(f"[OCR] '{filename}': Using AI Vision OCR ({result['page_count']} pages, model: {model})")

    # Convert PDF to images for Vision OCR
    images = pdf_to_images(pdf_path, dpi=150)

    # Debug: Save images to disk for inspection
    if os.getenv("DEBUG_OCR") == "true":
        save_images_for_debug(images, pdf_path)
        print(f"[DEBUG] Vision OCR would be called here, but skipping due to DEBUG mode")
        print(f"[DEBUG] Images saved. You can manually inspect them.")
        result["text"] = f"[DEBUG MODE] Images saved for inspection."
        result["method"] = "debug_skip_vision"
        return result

    text = await extract_text_with_vision(images, context=context, model=model)
    if not text.strip():
        raise RuntimeError(f"Kein OCR-Text extrahiert für Datei '{filename}' (Modell: {model})")
    print(f"[OCR] '{filename}': Vision OCR completed ({len(text)} chars, {len(images)} pages)")
    print(f"[OCR] KI-extrahierter Text von '{filename}':")
    print(f"  {'─'*60}")
    for line in text.split('\n'):
        print(f"  │ {line}")
    print(f"  {'─'*60}")
    result["text"] = text

    return result
