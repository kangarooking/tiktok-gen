# TikTokGen

Chinese version (default): [README.md](README.md)

An AI marketing short-video platform: pick avatar, voice, and script, then generate speech and final video automatically.

## Core Features

- Asset management: avatar / voice / script
- Quick Create: voice cloning, emotion control, preview synthesis
- Multi-provider configuration: TTS, digital human, cloud storage, LLM
- Async pipeline: Celery + Redis for generation jobs

## Tech Stack

- Frontend: React + TypeScript + Vite
- Backend: FastAPI + SQLAlchemy + Celery
- Infra: PostgreSQL + Redis + Docker Compose

## One-Command Deployment (Docker Compose)

```bash
cp .env.example .env
docker compose up -d
```

The database schema is available at `database/schema.sql`. Docker Compose imports it automatically when the PostgreSQL volume is created for the first time. If you use an external database, import it manually:

```bash
psql "$DATABASE_URL" -f database/schema.sql
```

After startup:
- Frontend: `http://localhost:3000`
- Backend: `http://localhost:3001`
- API docs: `http://localhost:3001/docs`

If ports are occupied, change `FRONTEND_PORT` and `BACKEND_PORT` in `.env`, and keep `VITE_API_URL` aligned.

Stop:

```bash
docker compose down
```

## Docker Hub Deployment

The release `docker-compose.yml` uses prebuilt images (no local build required).

```bash
cp .env.example .env
# default uses kangarooking/tiktokgen-* :v1.0.0
# edit .env only if you want a different namespace/tag
docker compose up -d
```

If you are a maintainer and need to publish images:

```bash
# run docker login first
./scripts/push_dockerhub.sh <dockerhub_namespace> <tag>
```

For local build workflow, use `docker-compose.dev.yml`.

## Local Development (Without Docker)

Backend:

```bash
cd backend
cp .env.example .env
pip install -r requirements.txt
python init_db.py
uvicorn app.main:app --reload --host 0.0.0.0 --port 3001
```

Worker (new terminal):

```bash
cd backend
celery -A app.tasks worker --loglevel=info --pool=solo
```

Frontend:

```bash
cd frontend
cp .env.example .env.local
npm install
npm run dev
```

## Project Structure

```text
.
├── frontend/          # React frontend
├── backend/           # FastAPI + Celery backend
├── database/          # PostgreSQL schema
├── docs/              # product and API docs
├── docker-compose.yml
└── AGENTS.md
```

## Open Source Notes

- Never commit real secrets: `.env`, OAuth secrets, cloud AK/SK
- Keep placeholders only in `backend/.env.example` and `.env.example`
- See `SECURITY.md` and `CONTRIBUTING.md`

## License

Apache-2.0
