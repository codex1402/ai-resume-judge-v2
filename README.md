# AI Resume Judge (Entry-Level ATS)

An **Entry-Level / New Graduate** ATS-style resume analyzer with a React (Vite) dashboard and a Flask backend powered by **Gemini 2.5 Flash** via the `google-genai` SDK.

## What it does

- Upload a resume PDF
- Extract text from the PDF
- Ask Gemini to generate a **strict JSON** ATS report (using `response_mime_type="application/json"`)
- Render a **SaaS-style dashboard**:
  - Overall score + verdict
  - 3 track scores (Product / Service / Incubator)
  - Strengths / Weaknesses / Actionable improvements
  - Technical + Behavioral interview questions

## Tech stack

- **Frontend**: React + Vite (`frontend/`)
- **Backend**: Python + Flask (`server.py`)
- **CORS**: `flask-cors`
- **PDF parsing**: `PyPDF2` (`backend/gatekeeper/resume_parser.py`)
- **LLM**: Gemini 2.5 Flash via `google-genai` (`backend/gatekeeper/judge.py`)
- **Config**: `.env` via `python-dotenv`

## Repo structure

```
ai-hire/
  server.py
  requirements.txt
  backend/
    gatekeeper/
      resume_parser.py
      judge.py
  frontend/
    package.json
    src/
      App.jsx
      App.css
  uploads/
```

## Prerequisites

- Python installed (recommended: Python 3.10+)
- Node.js installed (for the frontend)
- A Google Gemini API key

## Setup

### 1) Configure environment variables

Create/edit `.env` in the repo root:

```
GOOGLE_API_KEY=your_key_here
```

### 2) Install backend dependencies

From the repo root:

```bash
pip install -r requirements.txt
```

### 3) Run the backend

```bash
python server.py
```

Backend runs at `http://127.0.0.1:5000`.

### 4) Install and run the frontend

```bash
cd frontend
npm install
npm run dev
```

Open the Vite URL shown in the terminal (typically `http://localhost:5173`).

## API

### `POST /analyze`

Uploads a PDF resume and returns an ATS report.

- **Request**: `multipart/form-data`
  - `file`: PDF

- **Response**: JSON (always returns JSON; on errors returns a schema-shaped error payload)

Schema (shape):

```json
{
  "candidate_name": "String",
  "overall_score": 0,
  "verdict": "Shortlist | Borderline | Reject | ERROR",
  "track_scores": {
    "product_based": 0,
    "service_based": 0,
    "incubator_startup": 0
  },
  "detailed_analysis": {
    "strengths": [],
    "weaknesses": [],
    "actionable_improvements": []
  },
  "interview_questions": {
    "technical": "String",
    "behavioral": "String"
  }
}
```

## Troubleshooting

### `ModuleNotFoundError: No module named 'flask'`

Install backend deps:

```bash
pip install -r requirements.txt
```

### `ClientError: 429 RESOURCE_EXHAUSTED` (quota / rate limit)

You exceeded Gemini quota/rate limits. The backend will return a schema-shaped `"ERROR"` response with guidance.

Fix:

- Check Google Cloud / AI Studio quota and billing
- Wait for the quota to reset
- Reduce request frequency

### PDF text extraction is empty

Scanned/image PDFs often don’t contain extractable text. Try a text-based PDF or add OCR as a future enhancement.

## Notes

- This system is calibrated for **entry-level ATS scoring** (70–80 solid, 80–90 excellent).
- For deeper internals and diagrams, see `ARCHITECTURE.md`.

