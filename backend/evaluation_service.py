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
import re
from typing import Any, Dict, List, Optional
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


EVALUATION_SYSTEM_PROMPT = """Du bist ein erfahrener, fairer Universitäts-Prüfer und bewertest Klausuren.

Du erhältst:
1. Ein strukturiertes BEWERTUNGSRASTER (aus der Musterlösung extrahiert)
2. Die STUDENTENANTWORT (handschriftlich extrahierter Text einer Klausur)

Deine Aufgabe:
- Nutze EXAKT die Punktzahlen aus dem Bewertungsraster (niemals schätzen)
- Phase A: Ordne die Studentenantwort den Aufgaben/Teilaufgaben im Raster zu
- Phase B: Vergleiche inhaltlich + rechnerisch mit dem Raster und vergebe Punkte pro Aufgabe
- Phase C: Berechne konsistent total_points, max_points und overall_score
- Berücksichtige, dass der Text per OCR extrahiert wurde – kleine Tippfehler sind OK
- Sei fair aber genau in der Bewertung

WICHTIG – FOLGEFEHLER-REGELUNG:
- Ein FOLGEFEHLER liegt vor, wenn ein Student in einer früheren Aufgabe/Teilaufgabe einen Fehler macht und diesen falschen Wert korrekt in späteren Aufgaben weiterverwendet.
- Folgefehler werden mit NUR -1 Punkt Abzug bestraft (nicht mehr!). Der Rest der Aufgabe wird so bewertet, als wäre der fehlerhafte Wert korrekt gewesen.
- Beispiel: Wenn ein Student in Aufgabe 1 eine falsche Ableitung berechnet, aber diese falsche Ableitung korrekt in Aufgabe 2 einsetzt und damit richtig weiterrechnet, bekommt er für Aufgabe 2 volle Punkte minus 1 Punkt Folgefehler-Abzug.
- Markiere Folgefehler im Feedback klar als "Folgefehler aus Aufgabe X" und setze den Status auf "teilweise_korrekt" (NICHT "falsch").

WICHTIG – ALTERNATIVE LÖSUNGSWEGE:
- Wenn ein Student einen ANDEREN Lösungsweg als die Musterlösung wählt, aber dieser Weg mathematisch korrekt ist und zum richtigen Ergebnis führt, erhält er VOLLE Punktzahl.
- Auch wenn die Methode anders ist (z.B. L'Hôpital statt Polynomdivision, Substitution statt partielle Integration), zählt nur: Ist der Weg korrekt? Ist das Ergebnis richtig?
- Alternative korrekte Methoden NIEMALS als falsch bewerten!

WICHTIG – FAIRE BEWERTUNG:
- Bewerte den RECHENWEG, nicht nur das Endergebnis. Wenn der Rechenweg korrekt ist aber ein kleiner Rechenfehler zum falschen Ergebnis führt, gib Teilpunkte für den korrekten Weg.
- Kleine Rechenfehler (z.B. Vorzeichenfehler, Tippfehler bei Zahlen) = nur 1-2 Punkte Abzug, NICHT die gesamte Aufgabe als "falsch" werten.
- Eine Aufgabe darf nur den Status "falsch" bekommen, wenn der Lösungsansatz grundlegend falsch ist oder die Aufgabe komplett falsch bearbeitet wurde.
- "teilweise_korrekt" verwenden, wenn der Ansatz stimmt aber Fehler im Detail vorliegen.

WICHTIG zur Punktevergabe:
- "points_max" für jede Aufgabe MUSS exakt der Punktzahl im Bewertungsraster entsprechen
- "max_points" im Gesamtergebnis ist die Summe aller points_max aus den einzelnen Aufgaben
- "total_points" ist die Summe aller points_achieved
- "overall_score" = (total_points / max_points) * 100, gerundet auf ganze Zahlen
- Zahlenformate robust interpretieren (deutsch/englisch): 118.674,00 = 118674.00 = 118,674.00
- Runde nur dort, wo es fachlich sinnvoll ist, und dokumentiere Rundungen im Feedback

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
            "evidence": ["Originalstelle aus Studentenantwort", "verwendete Zahl oder Formel"],
            "grading_reason": "Kurze, präzise Begründung der Punktevergabe",
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

Die Punktzahlen dürfen NIEMALS geschätzt werden – sie müssen aus der Musterlösung/Aufgabenstellung stammen.
Antworte NUR mit dem JSON, ohne zusätzlichen Text."""


RUBRIC_SYSTEM_PROMPT = """Du extrahierst aus einer Musterlösung ein kompaktes Bewertungsraster für eine BWL/Kostenrechnungsklausur.

Liefere NUR JSON im Format:
{
  "tasks": [
    {
      "task_number": "1",
      "task_title": "Kostenartenrechnung",
      "points_max": 10,
      "task_type": "table_calc|numeric_calc|graph_interpretation|conceptual_text",
      "expected_elements": ["kurz und prüfbar"],
      "critical_values": ["zahlen/ergebnisse die wichtig sind"],
      "grading_rules": ["klare Teilpunkte oder Toleranzen"]
    }
  ],
  "total_points": 90,
  "notes": "optionale Hinweise"
}

Regeln:
- Aufgabenköpfe wie 'Aufgabe X (Y Punkte)' priorisieren.
- Wenn Punkte fehlen, sinnvolle Nullwerte setzen statt zu raten.
- Kurze, präzise, maschinenlesbare Felder."""

KNOWN_TASK_POINT_MATRIX: Dict[str, int] = {
    "1": 10,
    "2": 15,
    "3": 20,
    "4": 20,
    "5": 25,
}

KNOWN_TASK_TITLES: Dict[str, str] = {
    "1": "Kostenartenrechnung",
    "2": "Make-or-Buy Analyse",
    "3": "Kalkulation",
    "4": "Abweichungsanalyse",
    "5": "Kostenrechnung Grundlagen",
}


def _fallback_rubric() -> Dict[str, Any]:
    tasks = [
        {
            "task_number": "1",
            "task_title": "Kostenartenrechnung",
            "points_max": 10,
            "task_type": "table_calc",
            "expected_elements": ["zeitliche Abgrenzung", "sachliche Abgrenzung", "Kosten je Position"],
            "critical_values": ["Tabellenwerte pro Zeile"],
            "grading_rules": ["Teilpunkte pro korrekt gefuellter Zelle"],
        },
        {
            "task_number": "2",
            "task_title": "Make-or-Buy Analyse",
            "points_max": 15,
            "task_type": "numeric_calc",
            "expected_elements": ["Kostenvergleich", "kritische Menge", "qualitative Faktoren"],
            "critical_values": ["fixe/variable Kosten", "kritische Menge"],
            "grading_rules": ["Rechenweg und Ergebnis separat bewerten"],
        },
        {
            "task_number": "3",
            "task_title": "Kalkulation",
            "points_max": 20,
            "task_type": "numeric_calc",
            "expected_elements": ["Selbstkosten", "Verkaufspreis", "Preisuntergrenzen"],
            "critical_values": ["Renditebezug", "Kostenstufen"],
            "grading_rules": ["Teilpunkte bei korrekter Methode trotz Rechenfehler"],
        },
        {
            "task_number": "4",
            "task_title": "Abweichungsanalyse",
            "points_max": 20,
            "task_type": "graph_interpretation",
            "expected_elements": ["Soll/Ist/Verrechnete Kosten", "Preisabweichung", "Bewertung Methode"],
            "critical_values": ["Abweichungswerte", "Kostensaetze"],
            "grading_rules": ["Grafische Loesung als Teilleistung anerkennen"],
        },
        {
            "task_number": "5",
            "task_title": "Kostenrechnung Grundlagen",
            "points_max": 25,
            "task_type": "conceptual_text",
            "expected_elements": ["Fachbegriffe korrekt", "inhaltlich richtige Abgrenzungen"],
            "critical_values": [],
            "grading_rules": ["Semantisch bewerten, kein Wortlaut-Zwang"],
        },
    ]
    return {"tasks": tasks, "total_points": 90, "notes": "Fallback-Raster"}


def _safe_json_loads(raw: str) -> Dict[str, Any]:
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines)
    return json.loads(cleaned)


def _has_minimum_evaluation_schema(payload: Dict[str, Any]) -> bool:
    required = ["tasks", "general_feedback", "strengths", "weaknesses"]
    if not all(key in payload for key in required):
        return False
    if not isinstance(payload.get("tasks"), list):
        return False
    if not isinstance(payload.get("strengths"), list):
        return False
    if not isinstance(payload.get("weaknesses"), list):
        return False
    return True


def _to_number(value: Any) -> Optional[float]:
    if isinstance(value, (int, float)):
        return float(value)
    if value is None:
        return None

    text = str(value).strip()
    if not text:
        return None

    text = text.replace("EUR", "").replace("€", "").replace(" ", "")
    if "," in text and "." in text:
        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")
    elif "," in text:
        text = text.replace(",", ".")

    try:
        return float(text)
    except ValueError:
        return None


def _normalize_numeric_tokens(text: str) -> str:
    """Annotate numeric tokens in a model-friendly way while keeping source text intact."""
    lines: List[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        found = re.findall(r"[-+]?\d[\d.,\s]*", line)
        normalized_parts: List[str] = []
        for token in found:
            num = _to_number(token)
            if num is not None:
                normalized_parts.append(f"{token.strip()}=>{num:.6f}")

        if normalized_parts:
            lines.append(f"{line} [norm: {'; '.join(normalized_parts)}]")
        else:
            lines.append(line)

    return "\n".join(lines)


def _task_root(task_number: Any) -> str:
    token = str(task_number or "").strip()
    match = re.match(r"(\d+)", token)
    return match.group(1) if match else token


def _is_known_exam_rubric(rubric: Dict[str, Any]) -> bool:
    rubric_tasks = rubric.get("tasks", []) if isinstance(rubric.get("tasks"), list) else []
    task_roots = {_task_root(task.get("task_number")) for task in rubric_tasks}
    rubric_total = int(_to_number(rubric.get("total_points")) or 0)
    return set(KNOWN_TASK_POINT_MATRIX.keys()).issubset(task_roots) and rubric_total in (0, 90)


def _normalize_task_entries(tasks: List[Dict[str, Any]], use_known_matrix: bool, rubric_points: Dict[str, int]) -> List[Dict[str, Any]]:
    normalized: List[Dict[str, Any]] = []
    for raw in tasks:
        task = raw if isinstance(raw, dict) else {}
        task_num_raw = str(task.get("task_number", "")).strip() or "?"
        root = _task_root(task_num_raw)
        achieved = _to_number(task.get("points_achieved")) or 0.0

        if use_known_matrix:
            points_max = KNOWN_TASK_POINT_MATRIX.get(root, int(_to_number(task.get("points_max")) or 0))
            title = task.get("task_title") or KNOWN_TASK_TITLES.get(root, "Aufgabe")
        else:
            points_max = rubric_points.get(root, rubric_points.get(task_num_raw, int(_to_number(task.get("points_max")) or 0)))
            title = task.get("task_title") or "Aufgabe"

        points_max = max(0, int(points_max or 0))
        points_achieved = max(0.0, min(achieved, float(points_max))) if points_max > 0 else 0.0
        score_percent = round((points_achieved / float(points_max)) * 100) if points_max > 0 else 0

        normalized_task = {
            "task_number": task_num_raw,
            "task_title": title,
            "points_achieved": points_achieved,
            "points_max": points_max,
            "score_percent": score_percent,
            "status": task.get("status", "nicht_beantwortet"),
            "evidence": task.get("evidence", []),
            "grading_reason": task.get("grading_reason", "Punkte aus Rechenweg und Inhalt abgeleitet"),
            "feedback": task.get("feedback", ""),
            "missing_elements": task.get("missing_elements", []),
            "correct_elements": task.get("correct_elements", []),
        }
        normalized.append(normalized_task)

    return normalized


def _ensure_required_tasks(tasks: List[Dict[str, Any]], use_known_matrix: bool) -> List[Dict[str, Any]]:
    if not use_known_matrix:
        return tasks

    existing_roots = {_task_root(task.get("task_number")) for task in tasks}
    for root, max_points in KNOWN_TASK_POINT_MATRIX.items():
        if root in existing_roots:
            continue
        tasks.append(
            {
                "task_number": root,
                "task_title": KNOWN_TASK_TITLES.get(root, f"Aufgabe {root}"),
                "points_achieved": 0.0,
                "points_max": max_points,
                "score_percent": 0,
                "status": "nicht_beantwortet",
                "evidence": [],
                "grading_reason": "Aufgabe wurde in der Antwort nicht erkennbar bearbeitet.",
                "feedback": "Keine auswertbare Antwort erkannt.",
                "missing_elements": [],
                "correct_elements": [],
            }
        )

    return sorted(tasks, key=lambda t: (_task_root(t.get("task_number")), str(t.get("task_number", ""))))


def _grade_from_percent(score: float) -> str:
    if score >= 95:
        return "1.0"
    if score >= 90:
        return "1.3"
    if score >= 85:
        return "1.7"
    if score >= 80:
        return "2.0"
    if score >= 75:
        return "2.3"
    if score >= 70:
        return "2.7"
    if score >= 65:
        return "3.0"
    if score >= 60:
        return "3.3"
    if score >= 55:
        return "3.7"
    if score >= 50:
        return "4.0"
    return "5.0"


def _validate_and_fix_result(result: Dict[str, Any], rubric: Dict[str, Any]) -> Dict[str, Any]:
    raw_tasks = result.get("tasks", []) if isinstance(result.get("tasks"), list) else []
    rubric_tasks = rubric.get("tasks", []) if isinstance(rubric.get("tasks"), list) else []
    rubric_points = {_task_root(t.get("task_number")): int(t.get("points_max", 0) or 0) for t in rubric_tasks}
    use_known_matrix = _is_known_exam_rubric(rubric)
    tasks = _normalize_task_entries(raw_tasks, use_known_matrix=use_known_matrix, rubric_points=rubric_points)
    tasks = _ensure_required_tasks(tasks, use_known_matrix=use_known_matrix)

    total_points = 0.0
    max_points = 0.0
    for task in tasks:
        task.setdefault("evidence", [])
        task.setdefault("grading_reason", "Punkte aus Rechenweg und Inhalt abgeleitet")
        total_points += float(task.get("points_achieved", 0) or 0)
        max_points += float(task.get("points_max", 0) or 0)

    rubric_total = int(_to_number(rubric.get("total_points")) or 0)
    if use_known_matrix:
        max_points = float(sum(KNOWN_TASK_POINT_MATRIX.values()))
    elif rubric_total > 0:
        max_points = float(rubric_total)

    overall_score = round((total_points / max_points) * 100) if max_points > 0 else 0
    result["tasks"] = tasks
    result["total_points"] = round(total_points, 2)
    result["max_points"] = int(max_points)
    result["overall_score"] = overall_score
    result["overall_grade"] = _grade_from_percent(overall_score)
    result.setdefault("student_name", "Unbekannt")
    result.setdefault("general_feedback", "")
    result.setdefault("strengths", [])
    result.setdefault("weaknesses", [])
    return result


async def build_solution_rubric(solution_text: str, model: str = "openai/gpt-5.3-codex") -> Dict[str, Any]:
    """Build a structured rubric from model solution text."""
    fallback = _fallback_rubric()
    try:
        client = get_client()
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": RUBRIC_SYSTEM_PROMPT},
                {"role": "user", "content": f"## MUSTERLÖSUNG\n{solution_text}"},
            ],
            max_tokens=2000,
            temperature=0.1,
        )
        raw = getattr(response.choices[0].message, "content", "") if getattr(response, "choices", None) else ""
        if not raw:
            return fallback
        parsed = _safe_json_loads(raw)
        if not isinstance(parsed.get("tasks"), list) or len(parsed.get("tasks", [])) == 0:
            return fallback

        parsed.setdefault("total_points", sum(int(t.get("points_max", 0) or 0) for t in parsed["tasks"]))
        return parsed
    except Exception:
        return fallback


async def evaluate_exam(
    exam_text: str,
    solution_text: str,
    solution_rubric: Optional[Dict[str, Any]] = None,
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
    rubric = solution_rubric or _fallback_rubric()
    normalized_solution = _normalize_numeric_tokens(solution_text)
    normalized_exam = _normalize_numeric_tokens(exam_text)

    user_message = f"""## BEWERTUNGSRASTER (JSON):
{json.dumps(rubric, ensure_ascii=False)}

## MUSTERLÖSUNG (ORIGINAL):
{solution_text}

## MUSTERLÖSUNG (ZAHLEN NORMALISIERT):
{normalized_solution}

## STUDENTENANTWORT (ORIGINAL):
{exam_text}

## STUDENTENANTWORT (ZAHLEN NORMALISIERT):
{normalized_exam}"""

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

    try:
        result = _safe_json_loads(raw_response)
        if not isinstance(result, dict) or not _has_minimum_evaluation_schema(result):
            raise ValueError("Antwort verletzt das erwartete JSON-Schema")
    except Exception:
        try:
            repair = client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Konvertiere den folgenden Text in valides JSON mit diesen Pflichtfeldern: "
                            "student_name, overall_score, overall_grade, total_points, max_points, tasks, "
                            "general_feedback, strengths, weaknesses. "
                            "tasks muss eine Liste von Objekten sein mit task_number, points_achieved, points_max, "
                            "score_percent, status, evidence, grading_reason, feedback, missing_elements, correct_elements. "
                            "Antworte nur mit JSON."
                        ),
                    },
                    {"role": "user", "content": raw_response},
                ],
                max_tokens=4096,
                temperature=0,
            )
            repaired_raw = repair.choices[0].message.content or "{}"
            result = _safe_json_loads(repaired_raw)
            if not isinstance(result, dict) or not _has_minimum_evaluation_schema(result):
                raise ValueError("Reparierte Antwort ist kein valides Bewertungsschema")
        except Exception:
            result = {
                "error": "Bewertung konnte nicht als JSON geparst werden",
                "raw_response": raw_response,
                "overall_score": 0,
                "tasks": [],
                "general_feedback": raw_response,
            }

    return _validate_and_fix_result(result, rubric)


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
