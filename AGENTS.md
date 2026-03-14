# Repository Guidelines

## Project Structure & Module Organization
This repository has a split architecture:
- `frontend/`: React + TypeScript (Vite). Main UI code is in `pages/`, shared UI in `components/`, API calls in `services/`, and app bootstrap in `App.tsx` and `index.tsx`.
- `backend/`: FastAPI service. API routes live in `app/api/v1/`, business logic in `app/services/`, integrations in `app/integrations/`, data models in `app/models/`, and schemas in `app/schemas/`.
- `docs/`: product, API, and database documentation (`schema.sql`, interface docs).

Keep generated artifacts (`frontend/dist/`, `node_modules/`, `__pycache__/`) out of code reviews unless explicitly relevant.

## Build, Test, and Development Commands
Frontend (`frontend/`):
- `npm install`: install dependencies.
- `npm run dev`: start local Vite dev server.
- `npm run build`: produce production build in `frontend/dist/`.
- `npm run preview`: preview the production bundle.

Backend (`backend/`):
- `pip install -r requirements.txt`: install Python dependencies.
- `python init_db.py`: initialize database tables.
- `uvicorn app.main:app --reload --host 0.0.0.0 --port 3001`: run API locally.
- `celery -A app.tasks worker --loglevel=info --pool=solo`: run async worker.

## Coding Style & Naming Conventions
- Python: PEP 8, 4-space indentation, `snake_case` for functions/modules, `PascalCase` for classes.
- TypeScript/React: 2-space indentation, `PascalCase` for components (`AssetsStudio.tsx`), `camelCase` for variables/functions.
- Keep route files resource-oriented (`assets.py`, `projects.py`) and services action-oriented (`generation_service.py`).

## Testing Guidelines
- Backend test stack is `pytest` + `pytest-asyncio`.
- Place tests under `backend/tests/` using `test_*.py` naming.
- Run tests with: `pytest backend/tests -v`.
- Add at least one API-level test for new endpoints and one service-level test for non-trivial logic.

## Commit & Pull Request Guidelines
Git history is not available in this exported directory, so follow this standard:
- Commit format: `type(scope): short description` (example: `feat(api): add avatar upload validation`).
- Use focused commits; avoid mixing frontend/backend refactors with feature changes.
- PRs should include: summary, changed paths, verification steps, linked issue, and screenshots for UI changes.
- Call out config changes (`.env.example`, API keys, ports) explicitly in the PR description.

## Security & Configuration Tips
- Never commit real secrets in `.env`; keep placeholders in `backend/.env.example` and `frontend/.env.local`.
- Validate third-party API settings before deploy (GitHub OAuth, OSS, TTS/LLM/video providers).
- Verify CORS and callback URLs match environment-specific domains.
