"""
OCR Service – PDF to text extraction using PyMuPDF + OpenRouter Vision.

Flow:
1. PDF → Images (via PyMuPDF/fitz)
2. Images → structured OCR JSON (plain text, LaTeX, tables, diagrams, mindmaps)
3. Structured OCR → canonical text for downstream evaluation
"""

import base64
import asyncio
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import fitz  # PyMuPDF
from openai import OpenAI

_client: Optional[OpenAI] = None

OCR_REQUEST_TIMEOUT_SECONDS = int(os.getenv("OCR_REQUEST_TIMEOUT_SECONDS", "240"))
OCR_PAGE_RETRIES = int(os.getenv("OCR_PAGE_RETRIES", "2"))
OCR_MAX_OUTPUT_TOKENS = int(os.getenv("OCR_MAX_OUTPUT_TOKENS", "4096"))


def get_client() -> OpenAI:
    """Get or create the OpenRouter client (OpenAI-compatible)."""
    global _client
    if _client is None:
        # Prefer explicit OpenRouter key, but allow an OpenAI-compatible key as fallback
        api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "OPENROUTER_API_KEY (or OPENAI_API_KEY) is not set. "
                "Create a backend/.env from backend/.env.example and set OPENROUTER_API_KEY=<your_key>. "
                "Get a free key at https://openrouter.ai/keys"
            )
        _client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
            timeout=OCR_REQUEST_TIMEOUT_SECONDS,
            max_retries=1,
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


STRUCTURED_BLOCK_TYPES = {
    "text",
    "paragraph",
    "heading",
    "footer",
    "equation",
    "formula",
    "math",
    "table",
    "list",
    "form_fields",
    "graph",
    "mindmap",
    "diagram",
    "flowchart",
    "matrix",
    "unknown",
}


def _strip_code_fences(raw_text: str) -> str:
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
    return cleaned


def _safe_json_loads(raw_text: str) -> Optional[Dict[str, Any]]:
    cleaned = _strip_code_fences(raw_text)
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _looks_special_document(document: Dict[str, Any]) -> bool:
    pages = document.get("pages", [])
    if not isinstance(pages, list):
        return False
    for page in pages:
        if not isinstance(page, dict):
            continue
        blocks = page.get("blocks", [])
        if not isinstance(blocks, list):
            continue
        for block in blocks:
            if not isinstance(block, dict):
                continue
            block_type = str(block.get("type", "text")).lower()
            if block_type not in {"text", "heading"}:
                return True
    return False


def _format_table_markdown(block: Dict[str, Any]) -> str:
    headers = block.get("headers") or block.get("columns")
    rows = block.get("rows")

    markdown = block.get("markdown")
    if isinstance(markdown, str) and markdown.strip():
        return markdown.strip()

    if not isinstance(headers, list) or not isinstance(rows, list) or not headers:
        return str(block.get("text", "")).strip()

    def escape_cell(value: Any) -> str:
        return str(value).replace("|", "\\|").replace("\n", " ").strip()

    lines = ["| " + " | ".join(escape_cell(header) for header in headers) + " |"]
    lines.append("| " + " | ".join("---" for _ in headers) + " |")
    for row in rows:
        if isinstance(row, list):
            padded_row = row + [""] * (len(headers) - len(row))
            lines.append("| " + " | ".join(escape_cell(cell) for cell in padded_row[: len(headers)]) + " |")
    return "\n".join(lines)


def _render_block(block: Dict[str, Any]) -> str:
    block_type = str(block.get("type", "text")).lower()
    if block_type not in STRUCTURED_BLOCK_TYPES:
        block_type = "unknown"

    if block_type in {"text", "paragraph", "footer", "heading", "unknown"}:
        text = str(block.get("text", "")).strip()
        if block_type == "heading" and text:
            level = block.get("level", 2)
            if isinstance(level, int) and 1 <= level <= 6:
                return f"{'#' * level} {text}"
            return f"## {text}"
        return text

    if block_type == "form_fields":
        fields = block.get("fields", [])
        if isinstance(fields, list) and fields:
            lines: List[str] = []
            for field in fields:
                if isinstance(field, dict):
                    label = str(field.get("label", "")).strip()
                    value = str(field.get("value", "")).strip()
                    if label and value:
                        lines.append(f"{label}: {value}")
                    elif label:
                        lines.append(label)
                    elif value:
                        lines.append(value)
            if lines:
                return "\n".join(lines)
        return str(block.get("text", "")).strip()

    if block_type in {"equation", "formula", "math"}:
        latex = str(block.get("latex", block.get("text", ""))).strip()
        if not latex:
            return ""
        display = bool(block.get("display", True))
        return f"$$\n{latex}\n$$" if display else f"${latex}$"

    if block_type == "table":
        return _format_table_markdown(block)

    if block_type == "list":
        items = block.get("items", [])
        if isinstance(items, list) and items:
            ordered = bool(block.get("ordered", False))
            lines = []
            for index, item in enumerate(items, 1):
                item_text = str(item).strip()
                if not item_text:
                    continue
                prefix = f"{index}." if ordered else "-"
                lines.append(f"{prefix} {item_text}")
            return "\n".join(lines)
        return str(block.get("text", "")).strip()

    if block_type in {"graph", "mindmap", "diagram", "flowchart", "matrix"}:
        mermaid = str(block.get("mermaid", "")).strip()
        if mermaid:
            return f"```mermaid\n{mermaid}\n```"
        latex = str(block.get("latex", "")).strip()
        if latex:
            return f"$$\n{latex}\n$$"
        text = str(block.get("text", "")).strip()
        if text:
            return text
        nodes = block.get("nodes", [])
        edges = block.get("edges", [])
        if isinstance(nodes, list) and isinstance(edges, list):
            lines = ["- Knoten:"]
            for node in nodes:
                lines.append(f"  - {node}")
            if edges:
                lines.append("- Kanten:")
                for edge in edges:
                    lines.append(f"  - {edge}")
            return "\n".join(lines)
        return ""

    return str(block.get("text", "")).strip()


def _build_canonical_text(document: Dict[str, Any], fallback_text: str) -> str:
    rendered_pages: List[str] = []
    pages = document.get("pages", [])
    if isinstance(pages, list) and pages:
        for index, page in enumerate(pages, 1):
            if not isinstance(page, dict):
                continue
            page_number = page.get("page_number", index)
            blocks = page.get("blocks", [])
            page_lines: List[str] = [f"=== Seite {page_number} ==="]
            if isinstance(blocks, list):
                for block in blocks:
                    if isinstance(block, dict):
                        rendered = _render_block(block)
                        if rendered:
                            page_lines.append(rendered)
            if len(page_lines) > 1:
                rendered_pages.append("\n".join(page_lines))

    plain_text = str(document.get("plain_text", "")).strip()
    if rendered_pages and (_looks_special_document(document) or not plain_text):
        return "\n\n".join(rendered_pages)

    if plain_text:
        return plain_text

    if rendered_pages:
        return "\n\n".join(rendered_pages)

    return fallback_text.strip()


def _build_system_prompt(context: str, page_number: Optional[int] = None, total_pages: Optional[int] = None) -> str:
    base_prompt = (
        "Du bist ein OCR-Spezialist. Extrahiere den gesamten Inhalt der folgenden Seiten exakt und vollständig. "
        "Nutze eine kanonische, strukturierte Ausgabe, damit spätere Korrektur und Bewertung stabil bleibt. "
        "Gib AUSSCHLIESSLICH ein gültiges JSON-Objekt zurück, ohne Markdown außen herum und ohne zusätzlichen Text. "
        "Die Ausgabe muss die natürliche Lesereihenfolge der Seite widerspiegeln. "
        "Plain Text bleibt Plain Text, aber strukturierte Inhalte müssen explizit markiert werden. "
        "Falls etwas unsicher ist, nutze [unleserlich] statt zu raten. "
        "Mathematische Ausdrücke müssen als LaTeX in 'latex' stehen. "
        "Tabellen müssen als Tabelle mit Spalten, Zeilen und optionaler Markdown-Darstellung extrahiert werden. "
        "Graphen, Mindmaps, Flussdiagramme, Netzwerke und ähnliche Strukturen müssen als strukturierte Knoten-/Kantenrepräsentation oder als Mermaid-Code zurückgegeben werden. "
        "Listen und Aufzählungen müssen als Listen erhalten bleiben. "
        "Wenn die Struktur unklar ist, markiere den Block als 'unknown' und beschreibe nur das, was sicher lesbar ist."
    )

    plain_text_rules = (
        "Wenn die Seite nur Fließtext enthält, gib normale Textblöcke zurück. "
        "Wandle mathematische Zeichen weiter in LaTeX um, aber lass normalen Text normal. "
        "Wenn eine Seite mehrere Aufgaben oder Teilaufgaben enthält, trenne diese mit Headings oder separaten Textblöcken."
    )

    exam_rules = (
        "Es handelt sich um STUDENTENANTWORTEN. Extrahiere exakt das Geschriebene und interpretiere nichts um. "
        "Schreibe keine mathematisch 'besseren' oder 'richtigen' Werte hinein, wenn sie nicht klar lesbar sind. "
        "Bei Tabellen oder Skizzen soll die Struktur erhalten bleiben, auch wenn sie nicht perfekt lesbar ist. "
        "Für Mindmaps/Graphen soll die semantische Struktur erhalten bleiben (zentraler Knoten, Unterknoten, Kanten)."
    )

    solution_rules = (
        "Es handelt sich um MUSTERLÖSUNGEN. Extrahiere die Struktur so präzise wie möglich. "
        "Wenn die Lösung Tabellen, Matrizen, Diagramme, Mindmaps oder Graphen enthält, gib sie strukturiert zurück, damit die Bewertung sie eindeutig lesen kann."
    )

    page_hint = ""
    if isinstance(page_number, int) and isinstance(total_pages, int):
        page_hint = f" Du siehst genau Seite {page_number} von {total_pages}. Gib nur Inhalte dieser Seite aus."

    if context == "exam":
        return f"{base_prompt} {plain_text_rules} {exam_rules}{page_hint}"
    return f"{base_prompt} {plain_text_rules} {solution_rules}{page_hint}"


async def extract_text_with_vision(
    images: List[bytes],
    context: str = "exam",
    model: str = "google/gemini-2.0-flash-exp:free",
    page_number: Optional[int] = None,
    total_pages: Optional[int] = None,
) -> str:
    """Use AI Vision via OpenRouter to extract text from images (OCR).

    This returns canonical structured OCR text. Plain text is preserved, while
    tables, equations, graphs, mindmaps, and other layout-sensitive content are
    normalized into a stable representation for downstream evaluation.

    Args:
        images: List of PNG image bytes.
        context: Either 'exam' or 'solution' – adjusts the prompt.
        model: OpenRouter model ID.

    Returns:
        Canonical OCR text derived from structured JSON.
    """
    system_prompt = _build_system_prompt(context, page_number=page_number, total_pages=total_pages)

    client = get_client()

    # Build content with images (OpenAI Vision format – works with OpenRouter)
    content: list = [{"type": "text", "text": f"Bitte extrahiere den Text aus diesen {len(images)} Seiten:"}]
    b64_images = images_to_base64(images)
    for b64 in b64_images:
        content.append(
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{b64}",
                    "detail": "high",
                },
            }
        )

    response = await asyncio.to_thread(
        client.chat.completions.create,
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": content},
        ],
        max_tokens=OCR_MAX_OUTPUT_TOKENS,
        temperature=0.1,
    )
    return response.choices[0].message.content or ""


def _pdf_page_native_text(pdf_path: str, page_index: int) -> str:
    """Fallback extraction using native PDF text for one page."""
    try:
        with fitz.open(pdf_path) as doc:
            if 0 <= page_index < len(doc):
                text = doc[page_index].get_text("text")
                return text.strip()
    except Exception:
        return ""
    return ""


async def _extract_page_with_retry(
    image: bytes,
    context: str,
    model: str,
    page_number: int,
    total_pages: int,
) -> str:
    last_error: Optional[Exception] = None
    for attempt in range(1, OCR_PAGE_RETRIES + 2):
        try:
            return await extract_text_with_vision(
                [image],
                context=context,
                model=model,
                page_number=page_number,
                total_pages=total_pages,
            )
        except Exception as exc:
            last_error = exc
            if attempt <= OCR_PAGE_RETRIES:
                wait_seconds = min(2 * attempt, 6)
                print(f"[OCR] Seite {page_number}/{total_pages}: Versuch {attempt} fehlgeschlagen ({exc}). Neuer Versuch in {wait_seconds}s...")
                await asyncio.sleep(wait_seconds)
            else:
                break
    if last_error:
        raise RuntimeError(f"Vision OCR fehlgeschlagen auf Seite {page_number}: {last_error}")
    raise RuntimeError(f"Vision OCR fehlgeschlagen auf Seite {page_number}: Unbekannter Fehler")


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
        "method": "vision_ocr_structured",
        "text": "",
        "structured_document": {},
        "structured_mode": "structured_json",
        "has_special_layout": False,
        "page_count": 0,
        "quality": "ocr_structured",
    }

    # Get page count
    doc = fitz.open(pdf_path)
    result["page_count"] = len(doc)
    doc.close()

    print(f"[OCR] '{filename}': Using AI Vision OCR ({result['page_count']} pages, model: {model})")

    # Convert PDF to images for Vision OCR
    images = pdf_to_images(pdf_path, dpi=150)

    # Debug: Save images to disk for inspection
    if os.getenv("DEBUG_OCR") == "true":
        save_images_for_debug(images, pdf_path)
        print(f"[DEBUG] Vision OCR would be called here, but skipping due to DEBUG mode")
        print(f"[DEBUG] Images saved. You can manually inspect them.")
        result["text"] = f"[DEBUG MODE] Images saved for inspection."
        result["method"] = "debug_skip_structured_vision"
        return result

    total_pages = len(images)
    page_documents: List[Dict[str, Any]] = []
    page_plain_texts: List[str] = []
    warnings: List[str] = []

    for index, image in enumerate(images, start=1):
        print(f"[OCR] '{filename}': Seite {index}/{total_pages} wird verarbeitet...")
        try:
            raw_page_text = await _extract_page_with_retry(
                image=image,
                context=context,
                model=model,
                page_number=index,
                total_pages=total_pages,
            )
            structured_page_doc = _safe_json_loads(raw_page_text)

            if structured_page_doc is None:
                warnings.append(f"Seite {index}: Nicht-JSON-Antwort, als Plain Text übernommen.")
                page_text = raw_page_text.strip()
                page_documents.append(
                    {
                        "page": index,
                        "blocks": [{"type": "text", "text": page_text}],
                    }
                )
                page_plain_texts.append(page_text)
                continue

            page_entry: Dict[str, Any] = {"page": index, "blocks": []}
            pages = structured_page_doc.get("pages", [])
            if isinstance(pages, list) and pages and isinstance(pages[0], dict):
                page_entry["blocks"] = pages[0].get("blocks", [])
            elif isinstance(structured_page_doc.get("blocks"), list):
                page_entry["blocks"] = structured_page_doc.get("blocks", [])

            page_documents.append(page_entry)
            page_text = _build_canonical_text({"pages": [page_entry], "plain_text": structured_page_doc.get("plain_text", "")}, raw_page_text)
            page_plain_texts.append(page_text.strip())

        except Exception as e:
            native_text = _pdf_page_native_text(pdf_path, index - 1)
            fallback_text = native_text if native_text else "[OCR fehlgeschlagen auf dieser Seite]"
            warnings.append(f"Seite {index}: Vision OCR fehlgeschlagen ({e}); native PDF-Extraktion verwendet.")
            page_documents.append(
                {
                    "page": index,
                    "blocks": [{"type": "text", "text": fallback_text}],
                }
            )
            page_plain_texts.append(fallback_text)

    structured_document = {
        "document_type": context,
        "extraction_mode": "per_page_structured",
        "pages": page_documents,
        "plain_text": "\n\n".join([p for p in page_plain_texts if p]),
        "warnings": warnings,
    }

    canonical_text = _build_canonical_text(structured_document, structured_document.get("plain_text", ""))
    special_layout = _looks_special_document(structured_document)

    print(f"[OCR] '{filename}': Vision OCR completed ({len(canonical_text)} chars, {len(images)} pages)")
    print(f"[OCR] KI-extrahierter Text von '{filename}':")
    print(f"  {'─'*60}")
    for line in canonical_text.split('\n'):
        print(f"  │ {line}")
    print(f"  {'─'*60}")
    result["text"] = canonical_text
    result["structured_document"] = structured_document
    result["has_special_layout"] = special_layout

    return result
