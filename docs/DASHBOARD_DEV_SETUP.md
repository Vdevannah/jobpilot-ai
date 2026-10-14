# Local dashboard development (Phase 8C)

Two servers run side by side: the existing FastAPI backend and the new
`frontend/` React (Vite) app. Neither step here changes job discovery,
matching, AI agents, resume privacy, or the database schema.

## 1. Start the backend

From the repository root, with the existing virtual environment:

```sh
.venv/bin/uvicorn src.api:app --reload --port 8000
```

Confirm it's up: `curl http://localhost:8000/health` should return
`{"status":"ok"}`.

If port 8000 is already in use by another local project, pick a free port
instead (e.g. `--port 8010`) and point the frontend at it (see step 3).

## 2. Start the frontend

In a separate terminal:

```sh
cd frontend
npm install   # first time only
npm run dev
```

Vite serves the dashboard at `http://localhost:5173` by default. The
backend's CORS allowlist (`src/api.py`) only permits `localhost:5173` and
`127.0.0.1:5173` -- if that port is already taken on your machine and Vite
falls back to another port (watch its startup banner), either free port
5173 first, or update `ALLOWED_ORIGINS` in `src/api.py` to match.

## 3. Pointing the frontend at a non-default backend port

Copy `frontend/.env.example` to `frontend/.env` and set:

```
VITE_API_BASE_URL=http://localhost:8010
```

(or whatever host/port the backend is actually running on). Restart
`npm run dev` after changing this file.

## 4. Production build check

```sh
cd frontend
npm run build
```

This only verifies the frontend compiles; it does not need the backend
running.
