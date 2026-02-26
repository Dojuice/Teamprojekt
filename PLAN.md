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
- [ ] API-Endpunkt für mehrere PDFs / Ordner-Upload (`POST /api/upload-batch`)
- [ ] Datei-Validierung (nur PDF erlaubt)
- [ ] Temporäre Speicherung der hochgeladenen Dateien

### 2.3 OCR-Integration
- [ ] OCR-Service implementieren (EasyOCR oder OpenAI Vision)
- [ ] PDF → Bild-Konvertierung (pdf2image / PyMuPDF)
- [ ] Text-Extraktion aus handschriftlichen Antworten
- [ ] Qualitätsprüfung der OCR-Ergebnisse

### 2.4 KI-Bewertung
- [ ] OpenAI API-Anbindung (GPT-4 / Vision)
- [ ] Musterlösung-Verwaltung (Upload / Speicherung)
- [ ] Prompt-Engineering für semantischen Vergleich
- [ ] Bewertungslogik:
  - Korrektheitsscore (0–100%)
  - Fehlende Elemente identifizieren
  - Begründung / Erklärung generieren
- [ ] Ergebnis als strukturiertes JSON zurückgeben

### 2.5 Ergebnis-Download
- [ ] Korrigierte Klausur als PDF generieren (Bewertung + Kommentare)
- [ ] API-Endpunkt für Download (`GET /api/download/{id}`)
- [ ] Batch-Download als ZIP bei mehreren Klausuren

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
- [x] Sidebar mit Chat-Verlauf (erstellen, auswählen, löschen)
- [x] Chat-Nachrichten werden in DB persistiert
- [ ] Upload-Fortschrittsanzeige
- [ ] Bot-Antwort mit echtem Bewertungsergebnis (aktuell simulierte Antwort)
- [ ] Download-Button in der Bot-Antwort (korrigierte Klausur)

### 3.3 Styling & UX
- [x] Grundlegendes Styling (CSS für alle Komponenten)
- [x] Tooltips für Prompt-Buttons
- [ ] Responsive Design (Desktop & Tablet)
- [ ] Lade-Animationen während der Korrektur
- [ ] Fehlerbehandlung & Fehlermeldungen im Chat
- [ ] Drag & Drop für Datei-Upload

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
| KI / LLM       | OpenAI API (GPT-4) – geplant|
| OCR             | EasyOCR / OpenAI Vision – geplant |
| PDF-Verarbeitung| PyMuPDF / pdf2image – geplant|
| API-Doku        | Swagger (FastAPI built-in)   |
| Containerisierung| Docker Compose              |

## Meilensteine

| Meilenstein                          | Ziel-Zeitraum | Status       |
|--------------------------------------|---------------|--------------|
| Projektsetup abgeschlossen          | Woche 1       | ✅ Erledigt  |
| Chatbot-UI mit DB-Anbindung         | Woche 2       | ✅ Erledigt  |
| Backend-API (Upload + OCR) lauffähig | Woche 3–4     | 🔲 Offen     |
| KI-Bewertung funktionsfähig         | Woche 4–5     | 🔲 Offen     |
| Integration & Testing               | Woche 5–6     | 🔲 Offen     |
| MVP fertig & Präsentation           | Woche 7       | 🔲 Offen     |
