# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TikTokGen is an AI-powered digital human video generation platform. Users select digital human avatars, voice tones, and marketing scripts to automatically generate lip-synced short videos.

## Development Commands

### Frontend (from `/frontend`)
```bash
npm install        # Install dependencies
npm run dev        # Start dev server (port 3000)
npm run build      # Production build
npm run preview    # Preview production build
```

### Backend (from `/backend`)
```bash
pip install -r requirements.txt                      # Install dependencies
python init_db.py                                    # Initialize database
uvicorn app.main:app --reload --host 0.0.0.0 --port 3001  # Start API server
celery -A app.tasks worker --loglevel=info --pool=solo     # Start Celery worker (separate terminal)
pytest tests/ -v                                     # Run tests
alembic upgrade head                                 # Run database migrations
alembic revision --autogenerate -m "description"     # Create new migration
```

**Note**: Both FastAPI and Celery worker must run for video generation to work.

## Architecture

### Backend: FastAPI + Python (Layered Architecture)
- `app/main.py` - Application entry point with CORS, exception handlers, route registration
- `app/config.py` - Pydantic Settings for environment configuration
- `app/api/v1/` - REST endpoints (auth, users, assets, projects, generation)
- `app/services/` - Business logic layer
- `app/models/` - SQLAlchemy ORM models
- `app/schemas/` - Pydantic request/response schemas
- `app/integrations/` - Third-party service clients
- `app/tasks/` - Celery async tasks for video generation

### Frontend: React + TypeScript + Vite (SPA)
- Hash-based routing (`window.location.hash`)
- `pages/` - Page components (Landing, Dashboard, QuickCreate, AssetsStudio, Profile)
- `services/api.ts` - API client with fetch
- `services/hooks.ts` - Custom React hooks (useAuth, useAssets, useProjects, useProjectStatus)
- `i18n.ts` - Internationalization (English/Chinese via LanguageContext)

## Video Generation Flow

1. User selects avatar, voice, script → POST `/api/v1/projects`
2. Project created (status: PENDING)
3. Celery task: TTS generates audio (GENERATING_AUDIO)
4. Audio uploaded to OSS
5. WaveSpeed API generates video (GENERATING_VIDEO)
6. Video downloaded and uploaded to OSS
7. Project status updated to COMPLETED
8. Frontend polls `/api/v1/projects/{id}/status` for updates

## Third-Party Services

| Service | Purpose | Integration File |
|---------|---------|------------------|
| GitHub OAuth | User authentication | `integrations/github_oauth.py` |
| Index TTS | Text-to-speech | `integrations/index_tts.py` |
| WaveSpeed AI (302.ai) | Digital human video | `integrations/wavespeed_api.py` |
| GLM-4.7 | Marketing script generation | `integrations/glm_llm.py` |
| Aliyun OSS | File storage | `integrations/oss_storage.py` |
| Banana Pro | AI image generation | `integrations/banana_pro.py` |

## Database Models

- **User**: Accounts with tier subscription (free/pro/enterprise)
- **UserOAuthAccount**: OAuth provider associations
- **UserSession**: JWT session management
- **UserUsage**: Usage tracking (videos, minutes, storage)
- **Asset**: User assets (avatars, voices, scripts)
- **Project**: Video generation projects with status tracking
- **ProjectLog**: Generation process logs

## Ports

- Frontend: 3000
- Backend API: 3001
- Redis: 6379
- PostgreSQL: 5433 (as configured in .env)

## Required Services

- PostgreSQL 15+
- Redis 7.x
- Python 3.11+
- Node.js 18+
