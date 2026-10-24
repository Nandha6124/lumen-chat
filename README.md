# Lumen: Full-Stack AI Chat App

A complete AI product: React frontend, FastAPI backend, PostgreSQL database and an LLM layer (Google Gemini). Users register, log in and keep their own private chat history with persistent, multi-turn memory.

**Stack:** React + Vite, FastAPI, PostgreSQL, SQLAlchemy, JWT + bcrypt, Docker Compose, nginx, GitHub Actions

## Features
- Registration and login with **bcrypt**-hashed passwords and **JWT** access tokens
- Protected routes through a FastAPI dependency (`get_current_user`); every conversation is scoped to its owner, and other users get a 404
- Chat with the LLM, with per-conversation history sent as context (windowed to the last N messages)
- React UI: auth form, conversation sidebar, chat view, optimistic message display, error handling, responsive layout
- Failed LLM calls return a clean `502` and store nothing, so histories never contain unanswered messages
- Configuration via environment variables; separate local and production settings

## Project layout
```
backend/    FastAPI app, models, auth, tests, Dockerfile
frontend/   React app (Vite), Dockerfile, nginx.conf
docker-compose.yml   db + api + web
.github/workflows/ci.yml   backend tests and frontend build on every push / PR
```

## Run locally (no Docker)
Backend:
```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export GEMINI_API_KEY=your-key     # free: https://aistudio.google.com/apikey
uvicorn app.main:app --reload      # SQLite by default
```
Frontend (second terminal):
```bash
cd frontend
npm install
npm run dev                        # http://localhost:5173, proxies /api to :8000
```

## Run everything with Docker
```bash
cp .env.example .env     # fill in SECRET_KEY, POSTGRES_PASSWORD, GEMINI_API_KEY
docker compose up --build
```
Open http://localhost:8080.

## Tests
```bash
cd backend && pytest
```
Covers registration, login, password hashing, token validation (invalid and expired), per-user data isolation, chat memory, and LLM failure handling. The LLM is mocked.

## Deploy (Render example)
1. **Database:** create a Render PostgreSQL instance; copy its internal URL.
2. **API:** new Web Service from `backend/` (Docker). Set `DATABASE_URL` (use the `postgresql+psycopg2://` scheme), `SECRET_KEY`, `GEMINI_API_KEY` and `CORS_ORIGINS=https://<your-frontend-url>`.
3. **Frontend:** new Static Site from `frontend/` with build command `npm ci && npm run build`, publish directory `dist`, and env `VITE_API_URL=https://<your-api-url>`.
4. Add a custom domain in Render to get HTTPS certificates automatically.
