# Deployment Guide

This MVP can be deployed as one Docker Compose stack: Next.js frontend, FastAPI backend, PostgreSQL, and Redis.

## 1. Prepare The Server

Install Docker and Docker Compose on the server, then copy the repository there.

Create `.env` in the repository root. Required values:

```env
POSTGRES_PASSWORD=change-this-password
POSTGRES_DB=code_learn_assist
POSTGRES_USER=code_learn_assist
DATABASE_URL=postgresql+psycopg://code_learn_assist:change-this-password@postgres:5432/code_learn_assist
REDIS_URL=redis://redis:6379/0
YANDEX_GPT_ENDPOINT=https://ai.api.cloud.yandex.net/v1
YANDEX_GPT_API_KEY=your-api-key
YANDEX_GPT_MODEL=gpt://your-folder-id/qwen3.6-35b-a3b/latest
YANDEX_GPT_TIMEOUT_SECONDS=45
```

Do not put YandexGPT secrets into frontend files.

## 2. Start Production Stack

```bash
cd infra
docker compose --env-file ../.env -f docker-compose.prod.yml up --build -d
```

Open:

```text
http://your-server-ip
```

The frontend serves the app and proxies `/api/*` to the backend container through `BACKEND_INTERNAL_URL=http://backend:8000`. The browser does not need direct access to port `8000`.

## 3. Check Status

```bash
docker compose --env-file ../.env -f docker-compose.prod.yml ps
docker compose --env-file ../.env -f docker-compose.prod.yml logs -f backend
docker compose --env-file ../.env -f docker-compose.prod.yml logs -f frontend
```

To update:

```bash
git pull
cd infra
docker compose --env-file ../.env -f docker-compose.prod.yml up --build -d
```

## Why PostgreSQL Is Here

Redis is useful for fast temporary cache and generation locks, but it is not the long-term source of truth. PostgreSQL is needed for persistent generated lessons, review statuses, future users, progress history, error statistics, and recommendations.

Right now the MVP mostly works without PostgreSQL persistence wired deeply. For a real server, keep PostgreSQL in the stack so generated content can be saved permanently in the next iteration instead of paying YandexGPT repeatedly.
