# LogicLabs – KI-gestützte Klausurbewertung im internen Rechnungswesen

## Projektziel / Projektbeschreibung

Ziel des Projekts ist die Entwicklung eines Konzepts inklusive Proof of Concept für ein KI-basiertes Tool, das handschriftlich ausgefüllte Klausuren im Fach internes Rechnungswesen automatisch bewertet. Durch den Einsatz künstlicher Intelligenz soll die Korrekturzeit reduziert, die Objektivität erhöht und die Bewertung konsistent gestaltet werden.

Der Benutzer interagiert über eine **Chatbot-Weboberfläche**: Er lädt gescannte Klausuren (PDF) hoch und erhält die korrigierten Ergebnisse als Download zurück.

## Projektteam

- Dogukan Deniz
- Daniel Seewald
- Dominik Sünnboldt
- Pahwang Fotso Madeleine Leticia

## Ausgangssituation / Problemstellung

Derzeit erfolgt die Bewertung handschriftlich ausgefüllter Klausuren manuell. Diese Vorgehensweise ist zeitaufwendig, anfällig für subjektive Bewertung und schwer skalierbar. Besonders bei großen Teilnehmerzahlen stellt dies eine Herausforderung dar. KI-gestützte Texterkennung und Bewertungslogik bieten hier großes Potenzial.

## Workflow

1. Upload des gescannten Prüfungsbogens (PDF/JPG) über die Chatbot-Oberfläche
2. OCR extrahiert den Antwort-Text der Studierenden (z. B. via EasyOCR oder OpenAI Vision)
3. KI-Modell vergleicht die Antwort mit der Musterlösung
4. KI generiert:
   - Similarity- / Korrektheitsscore
   - Fehlende Elemente
   - Erklärung / Begründung
5. Ergebnis wird dem Benutzer als Download im Chat bereitgestellt

## Warum KI?

Klassisches Textmatching reicht nicht aus, weil Studierende:
- andere Formulierungen verwenden
- Argumente umstellen
- Schritte auslassen oder ergänzen
- Definitionen umschreiben
- anders herleiten

Ein LLM versteht **Bedeutung**, nicht nur Wörter.

## Technologie-Stack

| Bereich   | Technologie                        |
|-----------|------------------------------------|
| Frontend  | React (Chatbot-UI)                 |
| Backend   | Python + FastAPI                   |
| KI        | OpenAI API (GPT / Vision)         |
| OCR       | EasyOCR oder OpenAI Vision        |

## MVP-Umfang

- ✅ Chatbot-Weboberfläche (React)
- ✅ Datei-Upload (PDF / Ordner mit PDFs)
- ✅ OCR-Extraktion
- ✅ Semantischer Vergleich über OpenAI
- ✅ Korrektheitsscore
- ✅ Bewertungstext
- ✅ Download der korrigierten Klausur

## Risiken & Herausforderungen

- Qualität und Lesbarkeit handschriftlicher Klausuren
- Technische Grenzen der Erkennung und Interpretation
- Datenschutz bei der Verarbeitung personenbezogener Daten
- Akzeptanz durch Dozenten und Bildungseinrichtungen

## Budget / Ressourcen

Noch zu definieren (ggf. Software, Rechenkapazität, Zeitaufwand des Teams)

## Projektstruktur

```
├── frontend/           # React Chatbot-UI
│   ├── src/           # React source files
│   ├── public/        # Static files
│   ├── Dockerfile     # Frontend Docker configuration
│   └── package.json   # Node.js dependencies
├── backend/           # Python FastAPI Server
│   ├── server.py      # FastAPI application
│   ├── Dockerfile     # Backend Docker configuration
│   └── requirements.txt # Python dependencies
├── docker-compose.yml # Docker orchestration
├── .gitignore        # Git ignore rules
└── README.md
```

## Anwendung starten mit Docker

### Voraussetzungen
- Docker Desktop installiert
- Docker Compose verfügbar

### Starten der Anwendung

1. **Alle Container starten** (Backend startet zuerst, dann Frontend):
   ```bash
   docker-compose up --build
   ```

2. **Im Hintergrund starten**:
   ```bash
   docker-compose up -d --build
   ```

3. **Container stoppen**:
   ```bash
   docker-compose down
   ```

### Zugriff auf die Anwendung

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Dokumentation**: http://localhost:8000/docs

### Entwicklung

Die Volumes sind so konfiguriert, dass Änderungen am Code automatisch übernommen werden (Hot Reload):
- Frontend: Änderungen in `frontend/src/` werden automatisch neu geladen
- Backend: Änderungen in `backend/` werden automatisch neu geladen
