# AGENTS.md

FastAPI + React chat app with ComfyUI image generation. No tests or CI.

## Layout
- `backend/` — FastAPI app. Imports are package-relative (`from backend.…`), so **run uvicorn from the repo root**, not from `backend/`.
- `frontend/` — React 19 + Vite 8 + antd 6 + TypeScript. Package manager is **bun** (bun.lock). Linter is **oxlint** (`npm run lint`), not eslint.
- `comfyui_gen.py` — standalone ComfyUI client at root; imported by `backend/image_gen.py` via a `sys.path` hack.
- `llmchat/` — empty legacy dir; ignore.

## Run
- Backend (from repo root): `pip install -r requirements.txt && uvicorn backend.main:app --reload --port 8000`
  - Requires `.env` at repo root (`API_KEY`, `LOGIN_PASSWORD`, `MODEL_NAME`, `COMFYUI_BASE`, `COMFYUI_ZIMAGE_WORKFLOW`). `.env` contains real secrets — never print or commit them.
  - SQLite DB `chat.db` lives at repo root; schema is created on startup (`init_db`), no migrations.
  - `requests` is needed by `comfyui_gen.py` but missing from requirements.txt.
  - `COMFYUI_ZIMAGE_WORKFLOW` selects the z-image-turbo workflow; other workflows get their own env var. (Rename note: `backend/config.py` + `backend/image_gen.py` + `.env` must stay in sync.)
- Frontend: `bun install && bun run dev` (proxies `/api` → `127.0.0.1:8000`). Build: `bun run build` (runs `tsc -b && vite build`).

## Production serving
FastAPI mounts `frontend/dist` at `/` if the dir exists (backend/main.py:48). Rebuild the frontend (`bun run build`) for the backend to serve updated UI.

## Docker
- Everything lives in `deploy/`: `Dockerfile`, `build.sh`, `run_docker.sh`, `start.sh`. Repo-root `.dockerignore` keeps secrets/runtime data out of the build context.
- `./deploy/build.sh` builds `llmchat:latest` (ubuntu 24.04 + Aliyun/npmmirror mirrors; Python 3.12, Node 22, bun, ffmpeg). UID/GID build args default to the invoking user so files written into the mounted repo keep host ownership. The image is a pure toolchain env — code is NOT copied in.
- `./deploy/run_docker.sh` mounts the repo at `/workdir` and maps port 8000; the container then runs `/workdir/deploy/start.sh`.
- `start.sh` runs on every container start: `git pull --ff-only` (best-effort, never blocks startup), creates `/workdir/.venv` + `pip install -r requirements.txt`, `bun install && bun run build`, then `exec uvicorn backend.main:app --host 0.0.0.0 --port 8000`.
- No proxy is configured anywhere (build or runtime); if the network needs one, set it inside the container with `docker exec`.

## Auth
All `/api` routes except `/api/login` require `Authorization: Bearer <token>`; token comes from `POST /api/login` with `LOGIN_PASSWORD` from `.env`. Frontend stores it in `localStorage.token`.

## Gotchas
- NEVER run full-repo content search (grep/ripgrep over the repo root): `.venv/` and `frontend/node_modules/` contain hundreds of thousands of files and hang any recursive scan. Always scope searches to small paths (`backend/`, `frontend/src/`) or specific files.
- Chat (`POST /api/chat/{conv_id}`) is SSE streaming; the assistant reply is persisted to DB only after `[DONE]` is sent (backend/routes/chat.py:66). "New Chat" titles auto-rename from first user message.
- Image generation (`POST /api/images/generate`) needs a running ComfyUI at `COMFYUI_BASE` (default 127.0.0.1:8188) with the configured workflow; otherwise it 500s. Generated images are stored as BLOBs in SQLite and served at `/api/images/{id}`; the markdown image link is also appended to the message content.
- Backend comments, error messages, and UI text are in Chinese — keep new code/strings consistent.
