"""
OCR Service – PDF to text extraction using PyMuPDF + OpenRouter Vision.

Flow:
1. PDF → Images (via PyMuPDF/fitz)
2. Images → Text (via OpenRouter Vision API – any model with vision support)
3. Also supports direct text extraction from typed PDFs
"""

import fitz  # PyMuPDF
import base64
import io
import os
from pathlib import Path
from typing import List, Optional
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


def extract_text_direct(pdf_path: str) -> str:
    """Extract text directly from a PDF (works for typed/digital PDFs).

    Args:
        pdf_path: Path to the PDF file.

    Returns:
        Extracted text content.
    """
    doc = fitz.open(pdf_path)
    text_parts: List[str] = []

    for page_num, page in enumerate(doc, 1):
        text = page.get_text()
        if text.strip():
            text_parts.append(text.strip())

        # Debug: Print extracted text per page
        if os.getenv("DEBUG_OCR") == "true":
            print(f"\n=== Page {page_num} Direct Extraction ===")
            print(text if text.strip() else "[No text found]")
            print("=" * 50)

    doc.close()
    return "\n\n---\n\n".join(text_parts)


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
    if context == "exam":
        system_prompt = (
            "Du bist ein OCR-Spezialist. Extrahiere den gesamten Text aus den folgenden "
            "Klausur-Seiten. Achte besonders auf handschriftliche Antworten. "
            "Gib den Text strukturiert zurück – trenne verschiedene Aufgaben klar voneinander. "
            "Wenn du unsicher bist, markiere die Stelle mit [unleserlich]. "
            "Gib NUR den extrahierten Text zurück, keine Kommentare."
        )
    else:
        system_prompt = (
            "Du bist ein OCR-Spezialist. Extrahiere den gesamten Text aus den folgenden "
            "Musterlösungs-Seiten. Gib den Text strukturiert zurück – trenne verschiedene "
            "Aufgaben und Teilaufgaben klar voneinander. "
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

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": content},
        ],
        max_tokens=4096,
        temperature=0.1,
    )
    return response.choices[0].message.content or ""


async def extract_text_from_pdf(pdf_path: str, context: str = "exam", force_vision: bool = False, model: str = "google/gemini-2.0-flash-exp:free") -> dict:
    """Extract text from a PDF file – tries direct extraction first, falls back to Vision OCR.

    Args:
        pdf_path: Path to the PDF file.
        context: 'exam' or 'solution'.
        force_vision: If True, always use Vision OCR (for handwritten content).
        model: OpenRouter model ID.

    Returns:
        Dict with extracted text and metadata.
    """
    filename = Path(pdf_path).name
    result = {
        "filename": filename,
        "method": "direct",
        "text": "",
        "page_count": 0,
        "quality": "good",
    }

    # Get page count
    doc = fitz.open(pdf_path)
    result["page_count"] = len(doc)
    doc.close()

    # Step 1: Always try direct text extraction first (free, instant, no API call)
    direct_text = extract_text_direct(pdf_path)
    char_count = len(direct_text.strip())
    min_chars_per_page = 20  # expect at least 20 chars per page for typed PDFs
    min_threshold = max(50, result["page_count"] * min_chars_per_page)

    if char_count >= min_threshold and not force_vision:
        print(f"[OCR] '{filename}': Direct text extraction successful ({char_count} chars) – no API call needed")
        result["text"] = direct_text
        result["method"] = "direct"

        # Debug: Print extracted text
        if os.getenv("DEBUG_OCR") == "true":
            print(f"\n{'='*60}")
            print(f"EXTRACTED TEXT FROM '{filename}' (Direct Method):")
            print(f"{'='*60}")
            print(direct_text)
            print(f"{'='*60}\n")

        return result

    if char_count > 0 and not force_vision:
        print(f"[OCR] '{filename}': Direct extraction found only {char_count} chars (threshold: {min_threshold}), falling back to Vision OCR")
    elif force_vision:
        print(f"[OCR] '{filename}': force_vision=True, using Vision OCR")
    else:
        print(f"[OCR] '{filename}': No text found via direct extraction, falling back to Vision OCR")

    # Step 2: Fall back to Vision OCR (for handwritten/scanned PDFs)
    images = pdf_to_images(pdf_path, dpi=150)  # Lower DPI to reduce token usage

    # Debug: Save images to disk for inspection
    if os.getenv("DEBUG_OCR") == "true":
        save_images_for_debug(images, pdf_path)
        print(f"[DEBUG] Vision OCR would be called here, but skipping due to DEBUG mode")
        print(f"[DEBUG] Images saved. You can manually inspect them.")
        result["text"] = f"[DEBUG MODE] Direct extraction: {char_count} chars. Images saved for inspection."
        result["method"] = "debug_skip_vision"
        return result

    text = await extract_text_with_vision(images, context=context, model=model)
    result["text"] = text
    result["method"] = "vision_ocr"
    result["quality"] = "ocr"

    return result
