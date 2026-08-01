# Repository Guidelines

## Project Structure & Module Organization

This repository is a small monorepo for a Python code-typing trainer.

- `frontend/`: Next.js, React, and TypeScript app. Main UI lives in `frontend/app/`; practice-specific components and state are in `frontend/features/practice/`; API and typing utilities are in `frontend/lib/`.
- `backend/`: FastAPI service. API routers are in `backend/app/api/`; Pydantic schemas in `backend/app/schemas/`; service logic in `backend/app/services/`; SQLAlchemy models in `backend/app/models/`; YandexGPT integration in `backend/app/yandex_gpt/`.
- `backend/app/fallback_content/`: validated fallback lesson JSON.
- `frontend/tests/` and `backend/tests/`: frontend Vitest and backend pytest suites.
- `infra/`: Docker Compose and infrastructure scaffolding.

## Build, Test, and Development Commands

Frontend:

```bash
cd frontend
npm install
npm run dev      # Start Next.js locally
npm test         # Run Vitest tests
npm run build    # Type-check and build production bundle
```

Backend:

```bash
cd backend
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
python -m pytest
```

Use Python 3.12 or 3.13 for backend work. The pinned FastAPI/Pydantic stack is not verified on Python 3.14.

## Coding Style & Naming Conventions

Use TypeScript `strict` mode patterns in the frontend. Prefer functional React components, explicit types for shared data, and camelCase for variables/functions. Keep CSS in `frontend/app/globals.css` unless a component-specific style file becomes necessary.

Backend code should use type hints, Pydantic schemas for request/response validation, and snake_case module/function names. Keep YandexGPT secrets and prompt logic backend-only.

## Testing Guidelines

Use Vitest for frontend unit tests, especially typing comparison and session state logic. Name tests `*.test.ts` or `*.test.tsx`.

Use pytest for backend API and validation tests. Add tests for every new endpoint, model-response validator, cache path, and fallback behavior. Run both frontend and backend tests before submitting changes.

## Commit & Pull Request Guidelines

No Git history is present in this working directory, so use concise Conventional Commit-style messages, for example `feat: add practice session API` or `test: cover code comparison`.

Pull requests should include a short summary, commands run, screenshots for UI changes, linked issues when applicable, and notes about migrations, environment variables, or security-sensitive behavior.

## Security & Configuration Tips

Do not expose YandexGPT API keys, IAM tokens, prompts, or raw model responses to the browser. Validate all model JSON before returning it to users. Do not add server-side execution of user Python code in this MVP.
