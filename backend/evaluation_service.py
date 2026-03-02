"""
Evaluation Service – AI-powered exam correction via OpenRouter.

Uses the OpenAI-compatible API at openrouter.ai to access any model
(Gemini, GPT-4o, Llama, etc.) through a single unified interface.

Compares student answers against a model solution and provides:
- Per-question scores (0–100%)
- Overall score
- Missing elements
- Detailed feedback / explanations
"""

import os
import json
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


EVALUATION_SYSTEM_PROMPT = """Du bist ein erfahrener Universitäts-Prüfer und bewertest Klausuren.

Du erhältst:
1. Die MUSTERLÖSUNG (korrekte Antworten des Professors)
2. Die STUDENTENANTWORT (handschriftlich extrahierter Text einer Klausur)

Deine Aufgabe:
- Vergleiche die Studentenantwort semantisch mit der Musterlösung
- Bewerte JEDE erkennbare Aufgabe / Teilaufgabe einzeln
- Berücksichtige, dass der Text per OCR extrahiert wurde – kleine Tippfehler sind OK
- Sei fair aber genau in der Bewertung

Antworte IMMER im folgenden JSON-Format (kein Markdown, kein Code-Block):
{
  "student_name": "Name des Studenten (falls erkennbar, sonst 'Unbekannt')",
  "overall_score": 75,
  "overall_grade": "2.7",
  "total_points": 45,
  "max_points": 60,
  "tasks": [
    {
      "task_number": "1a",
      "task_title": "Kurze Beschreibung der Aufgabe",
      "points_achieved": 8,
      "points_max": 10,
      "score_percent": 80,
      "status": "teilweise_korrekt",
      "feedback": "Detailliertes Feedback zur Antwort...",
      "missing_elements": ["Element das fehlt"],
      "correct_elements": ["Was richtig war"]
    }
  ],
  "general_feedback": "Allgemeines Feedback zur gesamten Klausur...",
  "strengths": ["Stärken des Studenten"],
  "weaknesses": ["Schwächen / Verbesserungsmöglichkeiten"]
}

Regeln für status: "korrekt", "teilweise_korrekt", "falsch", "nicht_beantwortet"
Regeln für overall_grade: Deutsche Notenskala 1.0 - 5.0 (1.0 = sehr gut, 5.0 = nicht bestanden)

Wenn du die Punktzahl nicht genau bestimmen kannst, schätze sie basierend auf dem Prozentsatz.
Antworte NUR mit dem JSON, ohne zusätzlichen Text."""


async def evaluate_exam(
    exam_text: str,
    solution_text: str,
    additional_instructions: str = "",
    model: str = "google/gemini-2.0-flash-exp:free",
) -> dict:
    """Evaluate a student's exam against the model solution.

    Args:
        exam_text: OCR-extracted text from the student's exam.
        solution_text: Text from the professor's model solution.
        additional_instructions: Optional extra instructions from the user.
        model: OpenRouter model ID (e.g. 'google/gemini-2.0-flash-exp:free').

    Returns:
        Structured evaluation result as a dict.
    """
    user_message = f"""## MUSTERLÖSUNG:
{solution_text}

## STUDENTENANTWORT:
{exam_text}"""

    if additional_instructions:
        user_message += f"\n\n## ZUSÄTZLICHE ANWEISUNGEN:\n{additional_instructions}"

    client = get_client()
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": EVALUATION_SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        max_tokens=4096,
        temperature=0.2,
    )
    raw_response = response.choices[0].message.content or "{}"

    # Clean up response – remove markdown code blocks if present
    raw_response = raw_response.strip()
    if raw_response.startswith("```"):
        lines = raw_response.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        raw_response = "\n".join(lines)

    try:
        result = json.loads(raw_response)
    except json.JSONDecodeError:
        result = {
            "error": "Bewertung konnte nicht als JSON geparst werden",
            "raw_response": raw_response,
            "overall_score": 0,
            "tasks": [],
            "general_feedback": raw_response,
        }

    return result


def format_evaluation_as_text(evaluation: dict) -> str:
    """Format a structured evaluation result as readable chat text.

    Args:
        evaluation: The evaluation dict from evaluate_exam().

    Returns:
        Formatted text for the chat bot response.
    """
    if "error" in evaluation:
        return f"⚠️ Bewertungsfehler: {evaluation.get('error', 'Unbekannt')}\n\n{evaluation.get('general_feedback', '')}"

    lines: List[str] = []

    # Header
    student = evaluation.get("student_name", "Unbekannt")
    score = evaluation.get("overall_score", 0)
    grade = evaluation.get("overall_grade", "–")
    total = evaluation.get("total_points", "–")
    max_pts = evaluation.get("max_points", "–")

    lines.append(f"📋 **Bewertungsergebnis**")
    lines.append(f"Student: {student}")
    lines.append(f"Gesamtnote: **{grade}** ({score}%)")
    lines.append(f"Punkte: {total} / {max_pts}")
    lines.append("")

    # Per-task results
    tasks = evaluation.get("tasks", [])
    if tasks:
        lines.append("📝 **Aufgaben im Detail:**")
        lines.append("")
        for task in tasks:
            num = task.get("task_number", "?")
            title = task.get("task_title", "")
            pts = task.get("points_achieved", "?")
            pts_max = task.get("points_max", "?")
            status = task.get("status", "unbekannt")
            feedback = task.get("feedback", "")

            status_icon = {
                "korrekt": "✅",
                "teilweise_korrekt": "🟡",
                "falsch": "❌",
                "nicht_beantwortet": "⬜",
            }.get(status, "❓")

            lines.append(f"{status_icon} **Aufgabe {num}** – {title}")
            lines.append(f"   {pts}/{pts_max} Punkte")
            if feedback:
                lines.append(f"   {feedback}")

            missing = task.get("missing_elements", [])
            if missing:
                lines.append(f"   Fehlend: {', '.join(missing)}")
            lines.append("")

    # General feedback
    general = evaluation.get("general_feedback", "")
    if general:
        lines.append(f"💬 **Allgemeines Feedback:**")
        lines.append(general)
        lines.append("")

    # Strengths & Weaknesses
    strengths = evaluation.get("strengths", [])
    weaknesses = evaluation.get("weaknesses", [])

    if strengths:
        lines.append("💪 **Stärken:**")
        for s in strengths:
            lines.append(f"  • {s}")
        lines.append("")

    if weaknesses:
        lines.append("📌 **Verbesserungsmöglichkeiten:**")
        for w in weaknesses:
            lines.append(f"  • {w}")
        lines.append("")

    return "\n".join(lines)
