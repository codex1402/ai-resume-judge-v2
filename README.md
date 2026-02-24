# AI Hiring Lab

Full-stack hiring workflow with:
- Resume ATS analysis (`/analyze`)
- Timed secure assessment generation (`/generate_assessment`)
- Assessment evaluation (`/submit_assessment`)
- Candidate/session history from DB

## Stack

- Backend: Flask + SQLAlchemy + Groq (`server.py`)
- Frontend: React + Vite (`frontend/`)
- DB: SQLite (local) or Postgres (production via `DATABASE_URL`)

## Local Run

1. Backend env:
```bash
cp .env.example .env
```
Set `GROQ_API_KEY`.

2. Install backend deps:
```bash
pip install -r requirements.txt
```

3. Run backend:
```bash
python server.py
```

4. Frontend env:
```bash
cp frontend/.env.example frontend/.env
```

5. Run frontend:
```bash
cd frontend
npm install
npm run dev
```

## Production Deployment (Render)

This repo includes `render.yaml` for:
- `ai-hiring-lab-api` (Flask API)
- `ai-hiring-lab-frontend` (static Vite site)
- `ai-hiring-lab-db` (Postgres)

### Required env vars

- Backend:
  - `GROQ_API_KEY`
  - `CORS_ORIGINS` (set to frontend URL, e.g. `https://ai-hiring-lab-frontend.onrender.com`)
- Frontend:
  - `VITE_API_BASE_URL` (set to backend URL, e.g. `https://ai-hiring-lab-api.onrender.com`)

### Manual start command (if not using Blueprint)

```bash
gunicorn --bind 0.0.0.0:$PORT server:app
```

## Security Notes

- `.env` is gitignored and must never be committed.
- Rotate any leaked API keys immediately.
- For production, keep `FLASK_DEBUG=false`.
