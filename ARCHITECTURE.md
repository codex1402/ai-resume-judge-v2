# Architecture & System Design

This document explains the **end-to-end architecture**, key flows, and the **system design principles** used in the codebase.

## High-level architecture

- **React (Vite) frontend** collects a PDF resume and renders a dashboard.
- **Flask backend** exposes `POST /analyze` and orchestrates:
  - PDF storage
  - PDF → text extraction
  - LLM call (Gemini) for ATS evaluation
  - Returns strict JSON back to the UI

## Flow diagram (request → dashboard)

```mermaid
flowchart TD
  U[User] -->|Select PDF| FE[React/Vite\nfrontend/src/App.jsx]
  FE -->|POST /analyze\nmultipart/form-data| API[Flask\nserver.py]
  API -->|save PDF| DISK[(uploads/)]
  API -->|extract_text_from_pdf(path)| PARSER[PDF Parser\nbackend/gatekeeper/resume_parser.py\n(PyPDF2)]
  PARSER -->|resume text| API
  API -->|analyze_resume_ats(text)| ATS[ATS Analyzer\nbackend/gatekeeper/judge.py]
  ATS -->|generate_content\nresponse_mime_type=application/json| GEM[Gemini 2.5 Flash\ngoogle-genai SDK]
  GEM -->|strict JSON| ATS
  ATS -->|validated dict| API
  API -->|JSON| FE
  FE -->|Render dashboard| DASH[UI Sections\nScore, Tracks, Report, Questions]
```

## Components & responsibilities

### 1) Frontend: `frontend/src/App.jsx`

**Responsibilities**
- Capture a PDF from the user
- Upload it via `fetch()` using `FormData`
- Render the ATS JSON response into a dashboard
- Display helpful error states (network errors, API quota errors, etc.)

**Why this design**
- Keeps the UI purely presentational + API-calling logic in one place (simple, small app).
- Schema-shaped response enables deterministic rendering (no brittle parsing in UI).

### 2) Backend HTTP API: `server.py`

**Responsibilities**
- Provide a single endpoint `POST /analyze`
- Validate request input (`file` presence, non-empty filename)
- Save the PDF to `uploads/`
- Call:
  - `extract_text_from_pdf()` for text extraction
  - `analyze_resume_ats()` for ATS report
- Return JSON to the frontend

**Why this design**
- The HTTP layer is a thin orchestrator (keeps logic testable and separated).
- File saving makes parsing reproducible and debuggable.

### 3) PDF parsing: `backend/gatekeeper/resume_parser.py`

**Responsibilities**
- Extract text from PDF files using `PyPDF2`

**Notes**
- Text extraction quality depends on PDF structure.
- Scanned/image PDFs often require OCR (future enhancement).

### 4) ATS engine: `backend/gatekeeper/judge.py`

**Responsibilities**
- Build an **entry-level calibrated** ATS prompt (New Grad expectations)
- Call Gemini via `google-genai`
- Enforce strict JSON output using:
  - `response_mime_type="application/json"`
- Validate response schema to prevent UI breakage
- Handle common API failures:
  - **429 quota/rate-limit** → return schema-shaped `"ERROR"` payload with guidance
  - auth issues → return schema-shaped `"ERROR"` payload with guidance

**Why this design**
- Prompt calibration is the core control for “ATS-like scoring”.
- JSON MIME type + validation makes the system reliable under real usage.
- Graceful degradation avoids UI crashes and produces actionable error messages.

## Data contract (schema-first)

The ATS response must match this schema shape:

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

## System design principles used (mapped to code)

### Separation of Concerns
- **HTTP**: `server.py`
- **PDF parsing**: `resume_parser.py`
- **LLM reasoning + output shaping**: `judge.py`
- **Presentation**: `App.jsx` + `App.css`

This reduces coupling and makes each layer easier to debug and change.

### Single Responsibility Principle (SRP)
- Each module does “one job”:
  - parse PDFs
  - run ATS analysis
  - serve HTTP
  - render UI

### Contract-first / Schema-driven design
- The app relies on a strict JSON schema.
- The backend validates required keys before returning.
- The UI assumes schema stability and focuses on rendering.

### Defensive programming + fail-fast
- Input validation early in `server.py`
- Empty PDF-text detection and error response
- API error detection (quota/auth) and schema-shaped error payloads

### Stateless backend (horizontal scaling friendly)
- No server-side session state required.
- Each request is independent and returns a complete report.

### Observability (pragmatic)
- Backend prints key milestones (extract length, API call, validation).
- Error responses include human-readable steps (especially quota/auth failures).

## Future improvements (nice-to-have)

- **OCR support** for scanned resumes (e.g., `pytesseract` / cloud OCR).
- **Caching** by file hash to reduce repeated Gemini calls.
- **Streaming** responses (if desired) for better UX.
- **Async queue** (Celery/RQ) for large throughput and rate-limit smoothing.
- **Typed contracts** (Pydantic models) for stronger schema enforcement.

