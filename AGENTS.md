# AGENTS.md

FastAPI + React chat app with ComfyUI image generation. No tests or CI.

## Layout
- `backend/` — FastAPI app. Imports are package-relative (`from backend.…`), so **run uvicorn from the repo root**, not from `backend/`.
- `frontend/` — React 19 + Vite 8 + antd 6 + TypeScript. Package manager is **bun** (bun.lock). Linter is **oxlint** (`npm run lint`), not eslint.
- `comfyui_gen.py` — standalone ComfyUI client at root; imported by `backend/image_gen.py` via a `sys.path` hack.
- `llmchat/` — empty legacy dir; ignore.

## Run
- Backend (from repo root): `pip install -r requirements.txt && uvicorn backend.main:app --reload --port 8000`
  - Requires `.env` at repo root (`API_KEY`, `LOGIN_PASSWORD`, `MODEL_NAME`, `COMFYUI_BASE`, `COMFYUI_WORKFLOW`). `.env` contains real secrets — never print or commit them.
  - SQLite DB `chat.db` lives at repo root; schema is created on startup (`init_db`), no migrations.
  - `requests` is needed by `comfyui_gen.py` but missing from requirements.txt.
- Frontend: `bun install && bun run dev` (proxies `/api` → `127.0.0.1:8000`). Build: `bun run build` (runs `tsc -b && vite build`).

## Production serving
FastAPI mounts `frontend/dist` at `/` if the dir exists (backend/main.py:48). Rebuild the frontend (`bun run build`) for the backend to serve updated UI.

## Auth
All `/api` routes except `/api/login` require `Authorization: Bearer <token>`; token comes from `POST /api/login` with `LOGIN_PASSWORD` from `.env`. Frontend stores it in `localStorage.token`.

## Gotchas
- Chat (`POST /api/chat/{conv_id}`) is SSE streaming; the assistant reply is persisted to DB only after `[DONE]` is sent (backend/routes/chat.py:66). "New Chat" titles auto-rename from first user message.
- Image generation (`POST /api/images/generate`) needs a running ComfyUI at `COMFYUI_BASE` (default 127.0.0.1:8188) with the configured workflow; otherwise it 500s. Generated images are stored as BLOBs in SQLite and served at `/api/images/{id}`; the markdown image link is also appended to the message content.
- Backend comments, error messages, and UI text are in Chinese — keep new code/strings consistent.
