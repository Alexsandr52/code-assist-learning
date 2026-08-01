import asyncio
import json
import logging
import secrets
import time
from pathlib import Path
from typing import Any
from redis import Redis
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.config import Settings
from app.models.cache import ContentCache
from app.schemas.content import LearningContentPayload
from app.schemas.practice import PracticeSessionCreate, PracticeSessionOut, CompleteSessionIn
from app.services.catalog import is_allowed_selection
from app.services.content_validation import validate_learning_content
from app.yandex_gpt.client import YandexGPTClient, YandexGPTUnavailable


logger = logging.getLogger("app.services.content_service")


class PracticeSessionStore:
    def __init__(self) -> None:
        self.sessions: dict[str, PracticeSessionOut] = {}
        self.completed: dict[str, dict[str, Any]] = {}


session_store = PracticeSessionStore()

AUTO_VARIANT_COUNT = 24
GENERATION_RESPONSE_BUDGET_SECONDS = 12


class ContentService:
    def __init__(self, settings: Settings, db: Session | None = None):
        self.settings = settings
        self.db = db
        self.model_client = YandexGPTClient(settings)
        self.redis = Redis.from_url(settings.redis_url, decode_responses=True) if settings.redis_url else None

    async def create_practice_session(self, payload: PracticeSessionCreate) -> PracticeSessionOut:
        if not is_allowed_selection(payload.language, payload.library, payload.topic, payload.difficulty):
            raise LookupError("unknown or inactive practice selection")

        variant = payload.variant or self._random_variant()
        content, source = await self._get_content(payload, variant)
        session_id = f"session_{secrets.token_urlsafe(12)}"
        session = PracticeSessionOut(
            sessionId=session_id,
            source=source,
            language=content.language,
            library=content.library,
            topic=content.topic,
            difficulty=content.difficulty,
            blocks=content.blocks,
            exercise=content.exercise,
        )
        session_store.sessions[session_id] = session
        return session

    def get_practice_session(self, session_id: str) -> PracticeSessionOut:
        session = session_store.sessions.get(session_id)
        if not session:
            raise LookupError("practice session not found")
        return session

    def complete_practice_session(self, session_id: str, payload: CompleteSessionIn) -> dict[str, str]:
        if session_id not in session_store.sessions:
            raise LookupError("practice session not found")
        session_store.completed[session_id] = payload.model_dump()
        return {"sessionId": session_id, "status": "completed"}

    async def _get_content(self, payload: PracticeSessionCreate, variant: int) -> tuple[LearningContentPayload, str]:
        started_at = time.perf_counter()
        cache_key = self._cache_key(payload, variant)
        cached = self._read_cache(cache_key)
        if cached:
            logger.info("Content cache hit: key=%s elapsed=%.3fs", cache_key, time.perf_counter() - started_at)
            return cached, "cache"

        persisted = self._read_database(cache_key)
        if persisted:
            self._write_cache(cache_key, persisted)
            logger.info("Content database hit: key=%s elapsed=%.3fs", cache_key, time.perf_counter() - started_at)
            return persisted, "database"

        fallback = self._load_fallback(payload)
        if fallback:
            self._write_cache(cache_key, fallback)
            logger.info("Content file fallback hit: key=%s elapsed=%.3fs", cache_key, time.perf_counter() - started_at)
            return fallback, "fallback"

        if self._generation_configured():
            logger.info("Generating content via model: key=%s variant=%s", cache_key, variant)
            generated = await self._try_generate_with_budget(payload, cache_key, variant)
            if generated:
                logger.info("Generated content accepted: key=%s elapsed=%.3fs", cache_key, time.perf_counter() - started_at)
                return generated, "generated"
        else:
            logger.info("Generation is not configured: key=%s", cache_key)

        generic_fallback = self._build_generic_fallback(payload)
        self._write_cache(cache_key, generic_fallback)
        logger.info("Content generic fallback used: key=%s elapsed=%.3fs", cache_key, time.perf_counter() - started_at)
        return generic_fallback, "fallback"

    async def _try_generate_with_budget(
        self,
        payload: PracticeSessionCreate,
        cache_key: str,
        variant: int,
    ) -> LearningContentPayload | None:
        timeout_seconds = min(self.settings.yandex_gpt_timeout_seconds, GENERATION_RESPONSE_BUDGET_SECONDS)
        try:
            started_at = time.perf_counter()
            return await asyncio.wait_for(self._try_generate(payload, cache_key, variant), timeout=timeout_seconds)
        except TimeoutError:
            logger.warning(
                "Generation timed out after %.1fs: language=%s library=%s topic=%s difficulty=%s elapsed=%.3fs",
                timeout_seconds,
                payload.language,
                payload.library,
                payload.topic,
                payload.difficulty,
                time.perf_counter() - started_at,
            )
            return None

    async def _try_generate(self, payload: PracticeSessionCreate, cache_key: str, variant: int) -> LearningContentPayload | None:
        lock_key = f"lock:{cache_key}"
        lock_acquired = self._acquire_lock(lock_key)
        if not lock_acquired:
            return self._read_cache(cache_key)
        try:
            for _ in range(self.settings.max_generation_attempts):
                attempt_started_at = time.perf_counter()
                try:
                    logger.info(
                        "Generation attempt started: key=%s language=%s library=%s topic=%s difficulty=%s",
                        cache_key,
                        payload.language,
                        payload.library,
                        payload.topic,
                        payload.difficulty,
                    )
                    raw = await self.model_client.generate_learning_content(
                        {
                            "language": payload.language,
                            "library": payload.library,
                            "topic": payload.topic,
                            "difficulty": payload.difficulty,
                            "numberOfBlocks": 5,
                            "variant": variant,
                            "variantSeed": f"{payload.language}:{payload.library}:{payload.topic}:{payload.difficulty}:v{variant}:{secrets.token_hex(4)}",
                        }
                    )
                    content = validate_learning_content(raw)
                    self._write_database(cache_key, content)
                    self._write_cache(cache_key, content)
                    logger.info(
                        "Generation attempt succeeded: key=%s elapsed=%.3fs",
                        cache_key,
                        time.perf_counter() - attempt_started_at,
                    )
                    return content
                except Exception as exc:
                    logger.warning(
                        "Generation attempt failed: key=%s elapsed=%.3fs error=%s",
                        cache_key,
                        time.perf_counter() - attempt_started_at,
                        exc,
                    )
                    continue
            return None
        finally:
            self._release_lock(lock_key)

    def _cache_key(self, payload: PracticeSessionCreate, variant: int) -> str:
        return f"{payload.language}:{payload.library}:{payload.topic}:{payload.difficulty}:variant-{variant}:{self.settings.prompt_version}"

    def _random_variant(self) -> int:
        return 1 + secrets.randbelow(AUTO_VARIANT_COUNT)

    def _generation_configured(self) -> bool:
        endpoint = self.settings.yandex_gpt_endpoint or ""
        model = self.settings.yandex_gpt_model or ""
        if endpoint.rstrip("/").endswith("/v1") and not model.startswith("gpt://"):
            return False
        return bool(
            endpoint.startswith(("http://", "https://"))
            and self.settings.yandex_gpt_api_key
            and model
        )

    def _read_cache(self, key: str) -> LearningContentPayload | None:
        if not self.redis:
            return None
        try:
            raw = self.redis.get(key)
        except Exception:
            return None
        if not raw:
            return None
        return validate_learning_content(json.loads(raw))

    def _read_database(self, key: str) -> LearningContentPayload | None:
        if self.db is None:
            return None
        try:
            row = self.db.execute(select(ContentCache).where(ContentCache.cache_key == key)).scalar_one_or_none()
        except Exception:
            return None
        if row is None:
            return None
        try:
            return validate_learning_content(row.content_json)
        except Exception:
            return None

    def _write_database(self, key: str, content: LearningContentPayload) -> None:
        if self.db is None:
            return
        try:
            row = self.db.execute(select(ContentCache).where(ContentCache.cache_key == key)).scalar_one_or_none()
            if row is None:
                row = ContentCache(cache_key=key, content_json=content.model_dump(mode="json"), status="validated")
                self.db.add(row)
            else:
                row.content_json = content.model_dump(mode="json")
                row.status = "validated"
            self.db.commit()
        except Exception:
            self.db.rollback()

    def _write_cache(self, key: str, content: LearningContentPayload) -> None:
        if not self.redis:
            return
        try:
            self.redis.setex(key, self.settings.cache_ttl_seconds, content.model_dump_json())
        except Exception:
            return

    def _acquire_lock(self, key: str) -> bool:
        if not self.redis:
            return True
        try:
            return bool(self.redis.set(key, "1", nx=True, ex=self.settings.generation_lock_ttl_seconds))
        except Exception:
            return True

    def _release_lock(self, key: str) -> None:
        if not self.redis:
            return
        try:
            self.redis.delete(key)
        except Exception:
            return

    def _load_fallback(self, payload: PracticeSessionCreate) -> LearningContentPayload | None:
        candidates = [
            f"{payload.library}_{payload.topic.replace('-', '_')}_{payload.difficulty}.json",
        ]
        if payload.library == "requests" and payload.topic == "get-requests" and payload.difficulty == "beginner":
            candidates.append("requests_get_requests_beginner.json")
        base = Path(__file__).resolve().parents[1] / "fallback_content"
        for filename in candidates:
            path = base / filename
            if path.exists():
                return validate_learning_content(json.loads(path.read_text(encoding="utf-8")))
        return None

    def _build_generic_fallback(self, payload: PracticeSessionCreate) -> LearningContentPayload:
        snippets = self._generic_snippets(payload.library)
        content = {
            "language": payload.language,
            "library": payload.library,
            "topic": payload.topic,
            "difficulty": payload.difficulty,
            "blocks": snippets["blocks"],
            "exercise": snippets["exercise"],
        }
        return validate_learning_content(content)

    def _generic_snippets(self, library: str) -> dict[str, Any]:
        snippets_by_library: dict[str, dict[str, Any]] = {
            "pandas": {
                "blocks": [
                    {"title": "Импорт", "code": "import pandas as pd", "explanation": "Подключает pandas под стандартным псевдонимом pd."},
                    {"title": "Таблица", "code": "data = pd.DataFrame({\"name\": [\"Ada\", \"Linus\"], \"score\": [98, 95]})", "explanation": "Создаёт DataFrame из словаря со списками значений."},
                    {"title": "Выбор", "code": "scores = data[[\"name\", \"score\"]]\nprint(scores)", "explanation": "Выбирает нужные столбцы и выводит результат."},
                ],
                "exercise": {
                    "description": "Создайте DataFrame с именами и баллами, затем выведите только эти два столбца.",
                    "starterCode": "import pandas as pd\n\n",
                    "hint": "Передайте словарь в pd.DataFrame и выберите столбцы через двойные квадратные скобки.",
                    "solution": "import pandas as pd\n\ndata = pd.DataFrame({\"name\": [\"Ada\", \"Linus\"], \"score\": [98, 95]})\nprint(data[[\"name\", \"score\"]])",
                },
            },
            "numpy": {
                "blocks": [
                    {"title": "Импорт", "code": "import numpy as np", "explanation": "Подключает numpy под стандартным псевдонимом np."},
                    {"title": "Массив", "code": "values = np.array([2, 4, 6, 8])", "explanation": "Создаёт одномерный массив чисел."},
                    {"title": "Операция", "code": "doubled = values * 2\nprint(doubled)", "explanation": "Умножает каждый элемент массива без явного цикла."},
                ],
                "exercise": {
                    "description": "Создайте numpy-массив и прибавьте 10 к каждому элементу.",
                    "starterCode": "import numpy as np\n\n",
                    "hint": "Операции с массивом применяются ко всем элементам сразу.",
                    "solution": "import numpy as np\n\nvalues = np.array([2, 4, 6, 8])\nprint(values + 10)",
                },
            },
            "fastapi": {
                "blocks": [
                    {"title": "Импорт", "code": "from fastapi import FastAPI", "explanation": "Импортирует класс приложения FastAPI."},
                    {"title": "Приложение", "code": "app = FastAPI()", "explanation": "Создаёт объект приложения."},
                    {"title": "Маршрут", "code": "@app.get(\"/health\")\ndef health():\n    return {\"status\": \"ok\"}", "explanation": "Описывает GET-маршрут, который возвращает JSON-ответ."},
                ],
                "exercise": {
                    "description": "Создайте FastAPI-приложение с маршрутом /ping.",
                    "starterCode": "from fastapi import FastAPI\n\n",
                    "hint": "Создайте app = FastAPI(), затем добавьте функцию с декоратором @app.get.",
                    "solution": "from fastapi import FastAPI\n\napp = FastAPI()\n\n@app.get(\"/ping\")\ndef ping():\n    return {\"message\": \"pong\"}",
                },
            },
            "beautifulsoup": {
                "blocks": [
                    {"title": "Импорт", "code": "from bs4 import BeautifulSoup", "explanation": "Импортирует BeautifulSoup для разбора HTML."},
                    {"title": "HTML", "code": "html = \"<h1>Python</h1><p>Practice</p>\"", "explanation": "Сохраняет короткий HTML-фрагмент в строку."},
                    {"title": "Поиск", "code": "soup = BeautifulSoup(html, \"html.parser\")\nprint(soup.find(\"h1\").text)", "explanation": "Находит первый заголовок h1 и выводит его текст."},
                ],
                "exercise": {
                    "description": "Разберите HTML и выведите текст первого абзаца.",
                    "starterCode": "from bs4 import BeautifulSoup\n\nhtml = \"<p>Hello</p>\"\n",
                    "hint": "Создайте BeautifulSoup и используйте find(\"p\").text.",
                    "solution": "from bs4 import BeautifulSoup\n\nhtml = \"<p>Hello</p>\"\nsoup = BeautifulSoup(html, \"html.parser\")\nprint(soup.find(\"p\").text)",
                },
            },
            "matplotlib": {
                "blocks": [
                    {"title": "Импорт", "code": "import matplotlib.pyplot as plt", "explanation": "Подключает pyplot для построения графиков."},
                    {"title": "Данные", "code": "days = [1, 2, 3]\nvalues = [4, 7, 5]", "explanation": "Готовит списки координат для графика."},
                    {"title": "График", "code": "plt.plot(days, values)\nplt.title(\"Progress\")", "explanation": "Строит линейный график и задаёт заголовок."},
                ],
                "exercise": {
                    "description": "Постройте простой линейный график по двум спискам.",
                    "starterCode": "import matplotlib.pyplot as plt\n\n",
                    "hint": "Передайте два списка в plt.plot и добавьте title.",
                    "solution": "import matplotlib.pyplot as plt\n\ndays = [1, 2, 3]\nvalues = [4, 7, 5]\nplt.plot(days, values)\nplt.title(\"Progress\")",
                },
            },
            "sqlalchemy": {
                "blocks": [
                    {"title": "Импорт", "code": "from sqlalchemy import Column, Integer, String", "explanation": "Импортирует типы колонок для модели."},
                    {"title": "База", "code": "from sqlalchemy.orm import declarative_base\nBase = declarative_base()", "explanation": "Создаёт базовый класс для ORM-моделей."},
                    {"title": "Модель", "code": "class User(Base):\n    __tablename__ = \"users\"\n    id = Column(Integer, primary_key=True)\n    name = Column(String)", "explanation": "Описывает таблицу users с колонками id и name."},
                ],
                "exercise": {
                    "description": "Опишите ORM-модель Product с id и title.",
                    "starterCode": "from sqlalchemy import Column, Integer, String\nfrom sqlalchemy.orm import declarative_base\n\nBase = declarative_base()\n",
                    "hint": "Создайте класс Product(Base), задайте __tablename__ и две колонки.",
                    "solution": "from sqlalchemy import Column, Integer, String\nfrom sqlalchemy.orm import declarative_base\n\nBase = declarative_base()\n\nclass Product(Base):\n    __tablename__ = \"products\"\n    id = Column(Integer, primary_key=True)\n    title = Column(String)",
                },
            },
        }
        return snippets_by_library.get(library, {
            "blocks": [
                {"title": "Импорт", "code": "import requests", "explanation": "Подключает библиотеку requests для HTTP-запросов."},
                {"title": "Запрос", "code": "response = requests.get(\"https://example.com\")", "explanation": "Отправляет GET-запрос и сохраняет ответ."},
                {"title": "Статус", "code": "print(response.status_code)", "explanation": "Выводит HTTP-код ответа."},
            ],
            "exercise": {
                "description": "Отправьте GET-запрос и выведите статус ответа.",
                "starterCode": "import requests\n\n",
                "hint": "Используйте requests.get и атрибут status_code.",
                "solution": "import requests\n\nresponse = requests.get(\"https://example.com\")\nprint(response.status_code)",
            },
        })
