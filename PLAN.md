# LogicLabs – Projektplan

## Phase 1: Projektsetup & Grundstruktur

- [x] README mit Projektinformationen erstellen
- [x] Projektplan erstellen
- [x] Frontend-Ordner (React) anlegen
- [x] Backend-Ordner (Python/FastAPI) anlegen
- [x] Git-Repository initialisieren & `.gitignore` konfigurieren
- [x] Docker-Compose Setup (Backend, Frontend, PostgreSQL)

## Phase 2: Backend-Entwicklung (Python + FastAPI)

### 2.1 Grundgerüst
- [x] Python-Umgebung einrichten (venv + requirements.txt)
- [x] FastAPI-Projekt initialisieren (`server.py`)
- [x] Projektstruktur anlegen (`server.py`, `models.py`, `database.py`)
- [x] CORS-Middleware für Frontend-Anbindung konfigurieren
- [x] PostgreSQL-Datenbank mit SQLAlchemy angebunden
- [x] Datenmodelle erstellt (Chat, Message)
- [x] Chat-CRUD-API implementiert (erstellen, auflisten, lesen, umbenennen, löschen)
- [x] Nachrichten-API implementiert (Nachrichten hinzufügen, Auto-Titel)
- [x] Health-Check & Welcome-Endpunkt

### 2.2 Datei-Upload
- [x] API-Endpunkt für einzelnen Datei-Upload (`POST /api/upload`) – Grundgerüst
- [x] API-Endpunkt für mehrere PDFs / Ordner-Upload (`POST /api/chats/{id}/upload`)
- [x] Datei-Validierung (nur PDF erlaubt)
- [x] Temporäre Speicherung der hochgeladenen Dateien

### 2.3 OCR-Integration
- [x] OCR-Service implementieren (OpenAI Vision via GPT-4o)
- [x] PDF → Bild-Konvertierung (PyMuPDF/fitz)
- [x] Text-Extraktion aus handschriftlichen Antworten
- [x] Google Gemini Vision als alternatives OCR-Backend
- [x] Direkte Text-Extraktion entfernt – ausschließlich AI Vision OCR
- [x] LaTeX-Notation für mathematische Ausdrücke in OCR-Ausgabe (x^2, \lim, \frac etc.)
- [x] Neutraler Textextraktor: KI darf Zahlen/Symbole nicht interpretieren oder korrigieren
- [x] Backend-Konsolen-Logging: OCR-Fortschritt, extrahierter Text pro Klausur (Vision + Direct)

### 2.4 KI-Bewertung
- [x] OpenAI API-Anbindung (GPT-4o / Vision)
- [x] Google Gemini API-Anbindung (Gemini 2.0 Flash – kostenlos)
- [x] Multi-Model-Architektur (zur Laufzeit zwischen OpenAI und Gemini wechselbar)
- [x] Musterlösung-Verwaltung (Upload / Speicherung)
- [x] Prompt-Engineering für semantischen Vergleich
- [x] Bewertungslogik:
  - Korrektheitsscore (0–100%)
  - Fehlende Elemente identifizieren
  - Begründung / Erklärung generieren
- [x] Ergebnis als strukturiertes JSON zurückgeben
- [x] Punkteverteilung wird aus der Musterlösung extrahiert (nicht geschätzt)
- [x] Folgefehler-Regelung: nur -1 Punkt Abzug statt komplett falsch
- [x] Alternative Lösungswege werden akzeptiert (volle Punkte bei korrekter Methode)
- [x] Faire Teilpunkte: Rechenweg wird bewertet, kleine Fehler ≠ "falsch"
- [x] Backend-Konsolen-Logging: Korrektur-Fortschritt, Ergebnis pro Klausur mit Aufgabendetails
- [x] Jede Klausur hat eigenen API-Call (separate Bewertung pro Student)

### 2.5 Ergebnis-Download
- [x] Korrigierte Klausur als PDF generieren (Bewertung + Kommentare)
- [x] API-Endpunkt für Download (`GET /api/download/{id}`)
- [x] Batch-Download als ZIP bei mehreren Klausuren

### 2.6 Konfiguration & Umgebung
- [x] API-Keys über `.env` im Backend verwaltet (python-dotenv)
- [x] `.env.example` mit Platzhaltern für Teammitglieder
- [x] Docker-Compose referenziert keine API-Keys mehr (Backend lädt eigene `.env`)

## Phase 3: Frontend-Entwicklung (React)

### 3.1 Grundgerüst
- [x] React-Projekt erstellt (Create React App + TypeScript)
- [x] Projektstruktur angelegt (`components/Chat`, `Header`, `Prompt`, `Sidebar`)
- [x] TypeScript-Typen definiert (`types.ts`: FileAttachment, ChatMessageData, ChatSummary)
- [ ] Routing einrichten (React Router) – derzeit Single-Page ohne Router

### 3.2 Chatbot-UI
- [x] Chat-Fenster als Hauptansicht (erste Seite die der User sieht)
- [x] Bot-Begrüßungsnachricht beim Start (via `/api/welcome`)
- [x] Nachrichtenverlauf (Bot- & User-Nachrichten) mit Chat-Komponente
- [x] Datei-Upload im Chat (Klausur- & Lösungs-Buttons in Prompt-Leiste)
  - [x] Einzelne Dateien
  - [x] Mehrere Dateien
  - [x] Ordner-Upload (alle PDFs aus Ordner)
- [x] Sidebar mit Chat-Verlauf (erstellen, auswählen, löschen)
- [x] Chat-Nachrichten werden in DB persistiert
- [x] Upload-Fortschrittsanzeige
- [x] Bot-Antwort mit echtem Bewertungsergebnis
- [x] Download-Button in der Bot-Antwort (korrigierte Klausur)

### 3.3 KI-Modellauswahl
- [x] Model-Selector Dropdown in der Prompt-Leiste
- [x] GPT-5.3 Codex als Standard voreingestellt
- [x] GPT-5.2 Codex als alternative Option wählbar
- [x] Modell-Auswahl wird an Backend-API übergeben (`model` Query-Parameter)
- [x] Extraktionsmethoden-Auswahl (Auto/Vision/Direkt) implementiert und wieder entfernt – nur noch AI Vision OCR

### 3.4 Styling & UX
- [x] Grundlegendes Styling (CSS für alle Komponenten)
- [x] Tooltips für Prompt-Buttons
- [x] Farbige Buttons für Klausur (blau) / Lösung (grün) Unterscheidung
- [x] Cleane Chat-Ansicht (ohne Border, ohne Sender-Namen)
- [x] Responsive Design (Desktop & Tablet)
- [x] Lade-Animationen während der Korrektur
- [x] Fehlerbehandlung & Fehlermeldungen im Chat
- [x] Drag & Drop für Datei-Upload
- [x] Aufeinanderfolgende Bot-Nachrichten werden kompaktiert (in eine Nachricht zusammengefasst)
- [x] Streaming-Animation nur für neue Nachrichten (nicht beim Laden alter Chats)

## Phase 3.5: OCR-Optimierung (Branch: OCROptimization)

- [x] Backend-Konsolen-Logging für OCR-Extraktion (Fortschritt x/n, extrahierter Text)
- [x] Backend-Konsolen-Logging für KI-Bewertung (Fortschritt, Ergebnis pro Klausur)
- [x] Jede Klausur hat eigenen API-Call für OCR und Bewertung
- [x] Extraktionsmethoden-Auswahl implementiert (Auto/KI-Vision/Direkt) – später vereinfacht auf nur AI Vision
- [x] Direkte PDF-Text-Extraktion komplett entfernt – nur noch AI Vision OCR
- [x] LaTeX-Math-Notation in OCR-Ausgabe (x^2, \lim, \frac, \int etc.)
- [x] OCR-Neutralität: KI extrahiert exakt, was geschrieben steht (keine Interpretation/Korrektur)
- [x] Punkteverteilung wird aus Musterlösung extrahiert (nicht mehr geschätzt)
- [x] Folgefehler-Regelung: nur -1 Punkt Abzug bei korrekt weitergerechnetem Fehler
- [x] Alternative Lösungswege werden akzeptiert und voll bewertet
- [x] Faire Bewertung: Rechenweg zählt, kleine Rechenfehler ≠ gesamte Aufgabe falsch
- [x] Modell-Auswahl reduziert auf GPT-5.3 Codex + GPT-5.2 Codex

## Phase 4: Integration & Testing

- [x] Frontend ↔ Backend API-Anbindung (Chat CRUD, Nachrichten, Welcome)
- [ ] End-to-End-Tests mit echten Klausur-Scans
- [ ] OCR-Genauigkeit evaluieren & optimieren
- [ ] Bewertungsqualität mit manuellen Korrekturen vergleichen
- [ ] Edge Cases testen (schlechte Handschrift, leere Seiten, etc.)

## Phase 5: Feinschliff & Dokumentation

- [ ] Code-Dokumentation
- [ ] API-Dokumentation (Swagger/OpenAPI – automatisch durch FastAPI)
- [ ] Benutzerhandbuch / Anleitung
- [ ] Datenschutz-Konzept erstellen
- [ ] Abschlusspräsentation vorbereiten

---

## Technologie-Übersicht

| Komponente       | Technologie                  |
|-----------------|------------------------------|
| Frontend        | React + Create React App + TS|
| Backend         | Python + FastAPI             |
| Datenbank       | PostgreSQL 16 (Docker)       |
| ORM             | SQLAlchemy 2.0               |
| KI / LLM       | OpenAI API (GPT-5.3 Codex, GPT-5.2 Codex) via OpenRouter |
| OCR             | AI Vision OCR (OpenRouter Vision API) + PyMuPDF (PDF→Bilder) |
| PDF-Verarbeitung| PyMuPDF (fitz)               |
| PDF-Generierung | ReportLab                    |
| API-Doku        | Swagger (FastAPI built-in)   |
| Containerisierung| Docker Compose              |

## Meilensteine

| Meilenstein                          | Ziel-Zeitraum | Status       |
|--------------------------------------|---------------|--------------|
| Projektsetup abgeschlossen          | Woche 1       | ✅ Erledigt  |
| Chatbot-UI mit DB-Anbindung         | Woche 2       | ✅ Erledigt  |
| Backend-API (Upload + OCR) lauffähig | Woche 3–4     | ✅ Erledigt  |
| KI-Bewertung funktionsfähig         | Woche 4–5     | ✅ Erledigt  |
| Integration & Testing               | Woche 5–6     | 🔲 Offen     |
| MVP fertig & Präsentation           | Woche 7       | 🔲 Offen     |
