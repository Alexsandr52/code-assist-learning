# Code Learn Assist

MVP веб-приложения для практики синтаксиса Python и популярных библиотек через ручной набор коротких фрагментов кода.

## Возможности

- Выбор Python-библиотеки, темы и сложности без выпадающих списков.
- Темы для `beginner`, `intermediate` и `advanced` по `requests`, `pandas`, `numpy`, `FastAPI`, `BeautifulSoup`, `matplotlib`, `SQLAlchemy`.
- Тренажёр в одном окне: бледный эталонный код и цветная посимвольная подсветка введённого текста.
- Обработка `Tab`, `Enter`, `Backspace`, запрет paste, кнопки `Пропустить блок` и `К заданию`.
- Практическое задание с подсказкой, решением и корректным завершением сессии.
- Генерация уроков через YandexGPT только на backend.
- Кэширование контента: Redis -> PostgreSQL -> YandexGPT -> fallback.
- Production-ready Docker Compose stack: frontend, backend, PostgreSQL, Redis.

## Архитектура

```text
Browser
  -> Next.js frontend
  -> /api/* Next.js proxy
  -> FastAPI backend
  -> Redis cache / generation lock
  -> PostgreSQL persistent content cache
  -> YandexGPT
```

Секреты YandexGPT никогда не попадают в браузер. Frontend обращается к backend через same-origin `/api/*`.

## Локальная Разработка

Backend:

```bash
cd backend
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Открыть приложение:

```text
http://127.0.0.1:3000
```

## Docker Compose

Локально:

```bash
cd infra
docker compose --env-file ../.env up --build
```

Production:

```bash
cd infra
docker compose --env-file ../.env -f docker-compose.prod.yml up --build -d
```

Production frontend публикуется на `:80`, backend доступен только внутри Docker-сети.

## Переменные Окружения

Создайте `.env` в корне:

```env
POSTGRES_DB=code_learn_assist
POSTGRES_USER=code_learn_assist
POSTGRES_PASSWORD=change-this-password
DATABASE_URL=postgresql+psycopg://code_learn_assist:change-this-password@postgres:5432/code_learn_assist
REDIS_URL=redis://redis:6379/0
YANDEX_GPT_ENDPOINT=https://ai.api.cloud.yandex.net/v1
YANDEX_GPT_API_KEY=your-api-key
YANDEX_GPT_MODEL=gpt://your-folder-id/qwen3.6-35b-a3b/latest
YANDEX_GPT_TIMEOUT_SECONDS=45
```

Для локального запуска backend без Docker замените host `postgres` на `127.0.0.1`, если PostgreSQL запущен на машине.

## Проверки

Backend:

```bash
cd backend
python -m pytest
```

Frontend:

```bash
cd frontend
npm test
npm run build
```

Compose config:

```bash
docker compose --env-file .env -f infra/docker-compose.prod.yml config --services
```

## Зачем PostgreSQL И Redis

Redis нужен для быстрого кэша и lock-защиты от параллельной генерации одинакового урока.

PostgreSQL нужен как постоянное хранилище проверенного контента. После генерации валидный урок сохраняется в PostgreSQL, поэтому при рестарте приложения он не теряется и не требует нового запроса к YandexGPT. Это снижает задержку и стоимость.

## Ограничения MVP

- Пользовательский Python-код не выполняется.
- Docker sandbox для решений не реализован.
- Автоматическая проверка свободных решений не реализована.
- Авторизация и история пользователей пока не добавлены.
- Таблицы создаются автоматически на старте backend; Alembic-миграции стоит добавить перед серьёзным production-ростом.

Подробная инструкция выкладки: `DEPLOY.md`.
