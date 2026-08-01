# Code Learn Assist

MVP веб-приложения для практического изучения синтаксиса Python и популярных библиотек через ручной набор коротких фрагментов кода.

## Что реализовано

- Next.js frontend с выбором языка, библиотеки, темы и сложности.
- Собственный компонент тренировки без IDE-редактора.
- Точное посимвольное сравнение кода на клиенте, включая пробелы, переносы, кавычки и скобки.
- Обработка `Tab`, `Enter`, `Backspace`, запрет paste и подсчёт попыток вставки.
- Экран практического задания с подсказкой и решением.
- FastAPI backend с каталогом, созданием/получением/завершением practice session.
- Backend-only YandexGPT client abstraction, Pydantic-валидация и fallback-контент.
- Redis hooks для cache/lock; PostgreSQL SQLAlchemy-модели подготовлены для следующего этапа.

## Локальный запуск

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Backend:

```bash
cd backend
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Use Python 3.12 or 3.13 for the backend. The current pinned FastAPI/Pydantic stack is not verified on Python 3.14.

Docker Compose:

```bash
cd infra
docker compose up --build
```

Production deployment:

```bash
cd infra
docker compose --env-file ../.env -f docker-compose.prod.yml up --build -d
```

See `DEPLOY.md` for server setup details.

## Переменные окружения

Скопируйте `.env.example` в `.env` и заполните YandexGPT-переменные после сверки с актуальной документацией YandexGPT. Секреты используются только backend-сервисом.

## Ограничения MVP

- Пользовательский Python-код не выполняется.
- Docker sandbox и автоматическая проверка свободных решений не реализованы.
- PostgreSQL-модели есть, но сохранение generated content в БД требует следующего шага с Alembic migration/seed.
- Мобильный ввод поддерживается best-effort.
