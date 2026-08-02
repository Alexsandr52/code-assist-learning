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
TERMINAL_LIBRARIES = {"linux", "git", "conda", "docker"}


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

        if payload.library in TERMINAL_LIBRARIES:
            terminal_fallback = self._build_generic_fallback(payload)
            logger.info("Content terminal fallback used: key=%s elapsed=%.3fs", cache_key, time.perf_counter() - started_at)
            return terminal_fallback, "fallback"

        if self._generation_configured():
            logger.info("Generating content via model: key=%s variant=%s", cache_key, variant)
            generated = await self._try_generate_with_budget(payload, cache_key, variant)
            if generated:
                logger.info("Generated content accepted: key=%s elapsed=%.3fs", cache_key, time.perf_counter() - started_at)
                return generated, "generated"
        else:
            logger.info("Generation is not configured: key=%s", cache_key)

        generic_fallback = self._build_generic_fallback(payload)
        logger.info("Content generic fallback used: key=%s elapsed=%.3fs", cache_key, time.perf_counter() - started_at)
        return generic_fallback, "fallback"

    async def _try_generate_with_budget(
        self,
        payload: PracticeSessionCreate,
        cache_key: str,
        variant: int,
    ) -> LearningContentPayload | None:
        timeout_seconds = self._generation_timeout_seconds()
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

    def _generation_timeout_seconds(self) -> float:
        return min(self.settings.yandex_gpt_timeout_seconds, self.settings.generation_response_budget_seconds)

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
                            "numberOfBlocks": 4,
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
        snippets = self._generic_snippets(payload.library, payload.topic, payload.difficulty)
        content = {
            "language": payload.language,
            "library": payload.library,
            "topic": payload.topic,
            "difficulty": payload.difficulty,
            "blocks": snippets["blocks"],
            "exercise": snippets["exercise"],
        }
        return validate_learning_content(content)

    def _generic_snippets(self, library: str, topic: str, difficulty: str) -> dict[str, Any]:
        if library == "pandas":
            return self._pandas_snippets(topic, difficulty)
        if library == "re":
            return self._re_snippets(topic, difficulty)
        if library in TERMINAL_LIBRARIES:
            return self._terminal_snippets(library, topic, difficulty)

        snippets_by_library: dict[str, dict[str, Any]] = {
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

    def _pandas_snippets(self, topic: str, difficulty: str) -> dict[str, Any]:
        snippets_by_topic: dict[str, dict[str, Any]] = {
            "select-columns": {
                "blocks": [
                    {"title": "Импорт", "code": "import pandas as pd", "explanation": "Подключает pandas под стандартным псевдонимом pd."},
                    {"title": "Таблица", "code": "users = pd.DataFrame({\"name\": [\"Ada\", \"Linus\"], \"age\": [36, 54], \"city\": [\"London\", \"Helsinki\"]})", "explanation": "Создаёт таблицу с несколькими столбцами."},
                    {"title": "Столбцы", "code": "profile = users[[\"name\", \"city\"]]\nprint(profile)", "explanation": "Выбирает два нужных столбца через список имён."},
                ],
                "exercise": {
                    "description": "Выберите из DataFrame только столбцы product и price.",
                    "starterCode": "import pandas as pd\n\nitems = pd.DataFrame({\"product\": [\"book\", \"pen\"], \"price\": [12, 3], \"stock\": [5, 20]})\n",
                    "hint": "Для нескольких столбцов используйте двойные квадратные скобки.",
                    "solution": "import pandas as pd\n\nitems = pd.DataFrame({\"product\": [\"book\", \"pen\"], \"price\": [12, 3], \"stock\": [5, 20]})\nprint(items[[\"product\", \"price\"]])",
                },
            },
            "dataframes": {
                "blocks": [
                    {"title": "Импорт", "code": "import pandas as pd", "explanation": "Подключает pandas."},
                    {"title": "Данные", "code": "data = {\"city\": [\"Paris\", \"Rome\"], \"temp\": [21, 25]}", "explanation": "Готовит словарь со списками одинаковой длины."},
                    {"title": "DataFrame", "code": "weather = pd.DataFrame(data)\nprint(weather)", "explanation": "Создаёт DataFrame и выводит его."},
                ],
                "exercise": {
                    "description": "Создайте DataFrame с колонками name и score.",
                    "starterCode": "import pandas as pd\n\n",
                    "hint": "Передайте словарь в pd.DataFrame.",
                    "solution": "import pandas as pd\n\nscores = pd.DataFrame({\"name\": [\"Ada\", \"Linus\"], \"score\": [98, 95]})\nprint(scores)",
                },
            },
            "filter-rows": {
                "blocks": [
                    {"title": "Импорт", "code": "import pandas as pd", "explanation": "Подключает pandas."},
                    {"title": "Продажи", "code": "sales = pd.DataFrame({\"item\": [\"book\", \"pen\", \"bag\"], \"price\": [12, 3, 40]})", "explanation": "Создаёт таблицу товаров и цен."},
                    {"title": "Фильтр", "code": "expensive = sales[sales[\"price\"] > 10]\nprint(expensive)", "explanation": "Оставляет строки, где цена больше 10."},
                ],
                "exercise": {
                    "description": "Оставьте строки, где значение score не меньше 90.",
                    "starterCode": "import pandas as pd\n\nscores = pd.DataFrame({\"name\": [\"Ada\", \"Linus\", \"Guido\"], \"score\": [98, 87, 91]})\n",
                    "hint": "Сравните столбец score с порогом и передайте маску в DataFrame.",
                    "solution": "import pandas as pd\n\nscores = pd.DataFrame({\"name\": [\"Ada\", \"Linus\", \"Guido\"], \"score\": [98, 87, 91]})\nprint(scores[scores[\"score\"] >= 90])",
                },
            },
            "groupby": {
                "blocks": [
                    {"title": "Импорт", "code": "import pandas as pd", "explanation": "Подключает pandas."},
                    {"title": "Заказы", "code": "orders = pd.DataFrame({\"region\": [\"EU\", \"US\", \"EU\"], \"amount\": [100, 80, 120]})", "explanation": "Создаёт таблицу заказов по регионам."},
                    {"title": "Группировка", "code": "totals = orders.groupby(\"region\")[\"amount\"].sum()\nprint(totals)", "explanation": "Суммирует продажи внутри каждой группы."},
                ],
                "exercise": {
                    "description": "Посчитайте средний score для каждой команды.",
                    "starterCode": "import pandas as pd\n\nscores = pd.DataFrame({\"team\": [\"A\", \"B\", \"A\"], \"score\": [10, 8, 14]})\n",
                    "hint": "Сгруппируйте по team и вызовите mean для score.",
                    "solution": "import pandas as pd\n\nscores = pd.DataFrame({\"team\": [\"A\", \"B\", \"A\"], \"score\": [10, 8, 14]})\nprint(scores.groupby(\"team\")[\"score\"].mean())",
                },
            },
            "missing-values": {
                "blocks": [
                    {"title": "Импорт", "code": "import pandas as pd", "explanation": "Подключает pandas."},
                    {"title": "Пропуски", "code": "data = pd.DataFrame({\"name\": [\"Ada\", \"Linus\", None], \"score\": [98, None, 91]})", "explanation": "Создаёт таблицу с пропущенными значениями."},
                    {"title": "Заполнение", "code": "data[\"score\"] = data[\"score\"].fillna(0)\nprint(data)", "explanation": "Заменяет пропуски в числовом столбце на 0."},
                ],
                "exercise": {
                    "description": "Удалите строки, где отсутствует email.",
                    "starterCode": "import pandas as pd\n\nusers = pd.DataFrame({\"name\": [\"Ada\", \"Linus\"], \"email\": [\"ada@example.com\", None]})\n",
                    "hint": "Используйте dropna с subset.",
                    "solution": "import pandas as pd\n\nusers = pd.DataFrame({\"name\": [\"Ada\", \"Linus\"], \"email\": [\"ada@example.com\", None]})\nprint(users.dropna(subset=[\"email\"]))",
                },
            },
            "merge-join": {
                "blocks": [
                    {"title": "Импорт", "code": "import pandas as pd", "explanation": "Подключает pandas."},
                    {"title": "Таблицы", "code": "users = pd.DataFrame({\"user_id\": [1, 2], \"name\": [\"Ada\", \"Linus\"]})\norders = pd.DataFrame({\"user_id\": [1, 1], \"amount\": [20, 35]})", "explanation": "Создаёт две таблицы с общим ключом user_id."},
                    {"title": "Объединение", "code": "merged = orders.merge(users, on=\"user_id\", how=\"left\")\nprint(merged)", "explanation": "Добавляет данные пользователя к заказам."},
                ],
                "exercise": {
                    "description": "Объедините таблицы products и prices по product_id.",
                    "starterCode": "import pandas as pd\n\nproducts = pd.DataFrame({\"product_id\": [1, 2], \"name\": [\"book\", \"pen\"]})\nprices = pd.DataFrame({\"product_id\": [1, 2], \"price\": [12, 3]})\n",
                    "hint": "Используйте merge с параметром on.",
                    "solution": "import pandas as pd\n\nproducts = pd.DataFrame({\"product_id\": [1, 2], \"name\": [\"book\", \"pen\"]})\nprices = pd.DataFrame({\"product_id\": [1, 2], \"price\": [12, 3]})\nprint(products.merge(prices, on=\"product_id\"))",
                },
            },
            "datetime": {
                "blocks": [
                    {"title": "Импорт", "code": "import pandas as pd", "explanation": "Подключает pandas."},
                    {"title": "Даты", "code": "events = pd.DataFrame({\"date\": [\"2026-01-01\", \"2026-01-03\"], \"value\": [10, 14]})", "explanation": "Создаёт таблицу со строковыми датами."},
                    {"title": "Преобразование", "code": "events[\"date\"] = pd.to_datetime(events[\"date\"])\nevents[\"day\"] = events[\"date\"].dt.day", "explanation": "Преобразует строки в даты и извлекает день месяца."},
                ],
                "exercise": {
                    "description": "Преобразуйте столбец created_at в datetime и выведите год.",
                    "starterCode": "import pandas as pd\n\nlogs = pd.DataFrame({\"created_at\": [\"2026-02-10\", \"2026-03-12\"]})\n",
                    "hint": "Используйте pd.to_datetime и accessor dt.year.",
                    "solution": "import pandas as pd\n\nlogs = pd.DataFrame({\"created_at\": [\"2026-02-10\", \"2026-03-12\"]})\nlogs[\"created_at\"] = pd.to_datetime(logs[\"created_at\"])\nprint(logs[\"created_at\"].dt.year)",
                },
            },
            "pivot-tables": {
                "blocks": [
                    {"title": "Импорт", "code": "import pandas as pd", "explanation": "Подключает pandas."},
                    {"title": "Продажи", "code": "sales = pd.DataFrame({\"region\": [\"EU\", \"EU\", \"US\"], \"quarter\": [1, 2, 1], \"amount\": [100, 120, 90]})", "explanation": "Создаёт длинную таблицу продаж."},
                    {"title": "Pivot", "code": "report = sales.pivot_table(index=\"region\", columns=\"quarter\", values=\"amount\", aggfunc=\"sum\")\nprint(report)", "explanation": "Строит сводную таблицу по регионам и кварталам."},
                ],
                "exercise": {
                    "description": "Постройте pivot_table с суммой amount по manager и month.",
                    "starterCode": "import pandas as pd\n\nsales = pd.DataFrame({\"manager\": [\"Ann\", \"Ann\", \"Bob\"], \"month\": [1, 2, 1], \"amount\": [10, 15, 7]})\n",
                    "hint": "manager должен быть index, month должен быть columns.",
                    "solution": "import pandas as pd\n\nsales = pd.DataFrame({\"manager\": [\"Ann\", \"Ann\", \"Bob\"], \"month\": [1, 2, 1], \"amount\": [10, 15, 7]})\nprint(sales.pivot_table(index=\"manager\", columns=\"month\", values=\"amount\", aggfunc=\"sum\"))",
                },
            },
            "rolling-window": {
                "blocks": [
                    {"title": "Импорт", "code": "import pandas as pd", "explanation": "Подключает pandas для работы с временными рядами."},
                    {"title": "Ряд", "code": "sales = pd.DataFrame({\"day\": pd.date_range(\"2026-01-01\", periods=5), \"amount\": [10, 15, 13, 20, 18]})", "explanation": "Создаёт упорядоченный ряд дневных продаж."},
                    {"title": "Окно", "code": "sales[\"rolling_mean\"] = sales[\"amount\"].rolling(window=3).mean()\nprint(sales[[\"day\", \"rolling_mean\"]])", "explanation": "Считает скользящее среднее по окну из трёх строк."},
                ],
                "exercise": {
                    "description": "Добавьте столбец rolling_max с максимумом visits за последние 2 строки.",
                    "starterCode": "import pandas as pd\n\ntraffic = pd.DataFrame({\"day\": pd.date_range(\"2026-01-01\", periods=4), \"visits\": [30, 45, 40, 60]})\n",
                    "hint": "Вызовите rolling(window=2).max() у столбца visits.",
                    "solution": "import pandas as pd\n\ntraffic = pd.DataFrame({\"day\": pd.date_range(\"2026-01-01\", periods=4), \"visits\": [30, 45, 40, 60]})\ntraffic[\"rolling_max\"] = traffic[\"visits\"].rolling(window=2).max()\nprint(traffic)",
                },
            },
            "apply-transform": {
                "blocks": [
                    {"title": "Импорт", "code": "import pandas as pd", "explanation": "Подключает pandas."},
                    {"title": "Данные", "code": "orders = pd.DataFrame({\"region\": [\"EU\", \"US\", \"EU\"], \"amount\": [100, 80, 120]})", "explanation": "Создаёт таблицу заказов."},
                    {"title": "Transform", "code": "orders[\"region_total\"] = orders.groupby(\"region\")[\"amount\"].transform(\"sum\")\nprint(orders)", "explanation": "Добавляет сумму по группе в каждую исходную строку."},
                ],
                "exercise": {
                    "description": "Добавьте столбец centered: score минус средний score внутри команды.",
                    "starterCode": "import pandas as pd\n\nscores = pd.DataFrame({\"team\": [\"A\", \"A\", \"B\"], \"score\": [10, 14, 7]})\n",
                    "hint": "Используйте groupby(...).transform(\"mean\") и вычтите результат.",
                    "solution": "import pandas as pd\n\nscores = pd.DataFrame({\"team\": [\"A\", \"A\", \"B\"], \"score\": [10, 14, 7]})\nscores[\"centered\"] = scores[\"score\"] - scores.groupby(\"team\")[\"score\"].transform(\"mean\")\nprint(scores)",
                },
            },
        }

        return snippets_by_topic.get(topic) or snippets_by_topic.get(difficulty) or snippets_by_topic["dataframes"]

    def _re_snippets(self, topic: str, difficulty: str) -> dict[str, Any]:
        snippets_by_topic: dict[str, dict[str, Any]] = {
            "regex-functions": {
                "blocks": [
                    {"title": "search", "code": "import re\nline = \"INFO user=alice action=login\"\nmatch = re.search(r\"user=\\w+\", line)", "explanation": "search находит фрагмент в любой части строки."},
                    {"title": "fullmatch", "code": "email = \"ops@example.com\"\nis_valid = re.fullmatch(r\"[\\w.-]+@[\\w.-]+\", email) is not None", "explanation": "fullmatch проверяет, что вся строка соответствует шаблону."},
                    {"title": "findall", "code": "text = \"ids: 42, 108, 204\"\nids = re.findall(r\"\\d+\", text)\nprint(ids)", "explanation": "findall возвращает все найденные совпадения списком."},
                ],
                "exercise": {
                    "description": "Выберите подходящие функции: найдите status в строке лога, проверьте весь код заявки и извлеките все числа.",
                    "starterCode": "import re\n\nline = \"ERROR status=500 request=abc-42\"\ncode = \"REQ-2048\"\ntext = \"latency 120 ms, retry 2\"\n",
                    "hint": "Для фрагмента используйте search, для полной проверки fullmatch, для всех чисел findall.",
                    "solution": "import re\n\nline = \"ERROR status=500 request=abc-42\"\ncode = \"REQ-2048\"\ntext = \"latency 120 ms, retry 2\"\nstatus = re.search(r\"status=\\d+\", line)\nis_code = re.fullmatch(r\"REQ-\\d+\", code) is not None\nnumbers = re.findall(r\"\\d+\", text)\nprint(status.group(), is_code, numbers)",
                },
            },
            "character-classes": {
                "blocks": [
                    {"title": "Цифры", "code": "import re\ntext = \"order A17 costs 450\"\nvalues = re.findall(r\"\\d+\", text)", "explanation": "\\d находит цифровые последовательности."},
                    {"title": "Слова", "code": "slug = \"user_profile_2026\"\nparts = re.findall(r\"\\w+\", slug)\nprint(parts)", "explanation": "\\w подходит для букв, цифр и подчёркивания."},
                    {"title": "Пробелы", "code": "raw = \"name   email\\tstatus\"\ncolumns = re.split(r\"\\s+\", raw)\nprint(columns)", "explanation": "\\s помогает разбивать текст по любым пробельным символам."},
                ],
                "exercise": {
                    "description": "Извлеките код товара, число и домен из строки заказа.",
                    "starterCode": "import re\n\nline = \"item=BK-204 qty=12 email=ops@example.com\"\n",
                    "hint": "Комбинируйте \\w, \\d и явные символы вроде дефиса и точки.",
                    "solution": "import re\n\nline = \"item=BK-204 qty=12 email=ops@example.com\"\nitem = re.search(r\"item=[\\w-]+\", line).group()\nqty = re.search(r\"qty=\\d+\", line).group()\ndomain = re.search(r\"@[\\w.-]+\", line).group()\nprint(item, qty, domain)",
                },
            },
            "quantifiers": {
                "blocks": [
                    {"title": "Один или больше", "code": "import re\nline = \"disk usage 95 percent\"\nnumber = re.search(r\"\\d+\", line).group()", "explanation": "+ требует минимум одно повторение."},
                    {"title": "Необязательная часть", "code": "codes = [\"color\", \"colour\"]\nchecks = [re.fullmatch(r\"colou?r\", code) for code in codes]", "explanation": "? делает предыдущий символ необязательным."},
                    {"title": "Диапазон", "code": "pin = \"4921\"\nis_pin = re.fullmatch(r\"\\d{4,6}\", pin) is not None\nprint(is_pin)", "explanation": "{n,m} задаёт допустимое число повторений."},
                ],
                "exercise": {
                    "description": "Проверьте id пользователя, где префикс usr- обязателен, а число содержит от 3 до 5 цифр.",
                    "starterCode": "import re\n\nvalue = \"usr-1042\"\n",
                    "hint": "Используйте fullmatch и квантификатор {3,5}.",
                    "solution": "import re\n\nvalue = \"usr-1042\"\nis_user_id = re.fullmatch(r\"usr-\\d{3,5}\", value) is not None\nprint(is_user_id)",
                },
            },
            "anchors-boundaries": {
                "blocks": [
                    {"title": "Начало строки", "code": "import re\nline = \"ERROR payment failed\"\nis_error = re.search(r\"^ERROR\", line) is not None", "explanation": "^ проверяет начало строки."},
                    {"title": "Конец строки", "code": "path = \"/var/log/app.log\"\nis_log = re.search(r\"\\.log$\", path) is not None", "explanation": "$ проверяет конец строки."},
                    {"title": "Граница слова", "code": "text = \"cat scatter category\"\nwords = re.findall(r\"\\bcat\\b\", text)\nprint(words)", "explanation": "\\b не даёт найти cat внутри другого слова."},
                ],
                "exercise": {
                    "description": "Проверьте, что строка начинается с WARN и заканчивается числовым кодом.",
                    "starterCode": "import re\n\nline = \"WARN retry finished 204\"\n",
                    "hint": "Соедините ^, \\d+ и $ в одном шаблоне.",
                    "solution": "import re\n\nline = \"WARN retry finished 204\"\nmatched = re.search(r\"^WARN.*\\d+$\", line) is not None\nprint(matched)",
                },
            },
            "groups-extraction": {
                "blocks": [
                    {"title": "Группы", "code": "import re\nline = \"user=alice id=42\"\nmatch = re.search(r\"user=(\\w+) id=(\\d+)\", line)", "explanation": "Скобки сохраняют части совпадения для извлечения."},
                    {"title": "group", "code": "name = match.group(1)\nuser_id = int(match.group(2))\nprint(name, user_id)", "explanation": "group(1) и group(2) возвращают найденные подстроки."},
                    {"title": "Несколько строк", "code": "rows = [\"cpu=91%\", \"mem=74%\"]\nvalues = [re.search(r\"(\\w+)=(\\d+)%\", row).groups() for row in rows]", "explanation": "groups возвращает кортеж всех захваченных групп."},
                ],
                "exercise": {
                    "description": "Извлеките метод, путь и статус из строки HTTP-лога.",
                    "starterCode": "import re\n\nline = \"GET /api/users 200\"\n",
                    "hint": "Метод состоит из заглавных букв, статус из цифр.",
                    "solution": "import re\n\nline = \"GET /api/users 200\"\nmatch = re.search(r\"([A-Z]+)\\s+([^\\s]+)\\s+(\\d+)\", line)\nmethod, path, status = match.groups()\nprint(method, path, int(status))",
                },
            },
            "findall-finditer": {
                "blocks": [
                    {"title": "findall", "code": "import re\ntext = \"user=alice user=bob user=carol\"\nusers = re.findall(r\"user=(\\w+)\", text)", "explanation": "findall удобен, когда нужны только значения."},
                    {"title": "finditer", "code": "line = \"10ms 25ms 80ms\"\nfor match in re.finditer(r\"\\d+ms\", line):\n    print(match.group(), match.start())", "explanation": "finditer даёт объект match и позиции совпадения."},
                    {"title": "Пары", "code": "query = \"page=2&limit=50\"\npairs = re.findall(r\"(\\w+)=(\\d+)\", query)\nprint(dict(pairs))", "explanation": "Группы в findall возвращаются кортежами."},
                ],
                "exercise": {
                    "description": "Соберите все request_id из текста и напечатайте их позиции.",
                    "starterCode": "import re\n\ntext = \"request_id=ab12 ok request_id=cd34 failed\"\n",
                    "hint": "Для значений хватит findall, для позиций нужен finditer.",
                    "solution": "import re\n\ntext = \"request_id=ab12 ok request_id=cd34 failed\"\nids = re.findall(r\"request_id=(\\w+)\", text)\npositions = [match.start() for match in re.finditer(r\"request_id=\\w+\", text)]\nprint(ids, positions)",
                },
            },
            "split-sub": {
                "blocks": [
                    {"title": "split", "code": "import re\nraw = \"alice, bob;carol  dave\"\nnames = re.split(r\"[,;\\s]+\", raw)", "explanation": "split с регулярным выражением разбивает по разным разделителям."},
                    {"title": "sub", "code": "phone = \"+1 (555) 010-2040\"\ndigits = re.sub(r\"\\D+\", \"\", phone)\nprint(digits)", "explanation": "sub заменяет все нецифровые фрагменты пустой строкой."},
                    {"title": "Очистка", "code": "title = \"  API---Gateway   Errors \"\nslug = re.sub(r\"\\W+\", \"-\", title.strip().lower())", "explanation": "sub помогает нормализовать текстовые поля."},
                ],
                "exercise": {
                    "description": "Разбейте строку тегов и нормализуйте телефон до одних цифр.",
                    "starterCode": "import re\n\ntags = \"error, api; retry  timeout\"\nphone = \"+7 (999) 123-45-67\"\n",
                    "hint": "Для тегов используйте split по запятым, точкам с запятой и пробелам; для телефона замените \\D+.",
                    "solution": "import re\n\ntags = \"error, api; retry  timeout\"\nphone = \"+7 (999) 123-45-67\"\nclean_tags = [tag for tag in re.split(r\"[,;\\s]+\", tags) if tag]\ndigits = re.sub(r\"\\D+\", \"\", phone)\nprint(clean_tags, digits)",
                },
            },
            "flags": {
                "blocks": [
                    {"title": "IGNORECASE", "code": "import re\ntext = \"Error: timeout\"\nfound = re.search(r\"error\", text, re.IGNORECASE) is not None", "explanation": "IGNORECASE отключает зависимость от регистра."},
                    {"title": "MULTILINE", "code": "log = \"INFO start\\nERROR fail\"\nerrors = re.findall(r\"^ERROR.*\", log, re.MULTILINE)", "explanation": "MULTILINE позволяет ^ и $ работать на каждой строке."},
                    {"title": "DOTALL", "code": "html = \"<pre>first\\nsecond</pre>\"\nbody = re.search(r\"<pre>.*</pre>\", html, re.DOTALL).group()", "explanation": "DOTALL позволяет точке захватывать перевод строки."},
                ],
                "exercise": {
                    "description": "Найдите все строки с error в многострочном логе независимо от регистра.",
                    "starterCode": "import re\n\nlog = \"info start\\nERROR failed\\nwarning retry\\nerror timeout\"\n",
                    "hint": "Объедините IGNORECASE и MULTILINE через оператор |.",
                    "solution": "import re\n\nlog = \"info start\\nERROR failed\\nwarning retry\\nerror timeout\"\nerrors = re.findall(r\"^error.*\", log, re.IGNORECASE | re.MULTILINE)\nprint(errors)",
                },
            },
            "named-groups": {
                "blocks": [
                    {"title": "Имена групп", "code": "import re\nline = \"2026-08-02 ERROR payment\"\npattern = r\"(?P<date>\\d{4}-\\d{2}-\\d{2}) (?P<level>\\w+) (?P<msg>.*)\"", "explanation": "Именованные группы делают шаблон самодокументируемым."},
                    {"title": "groupdict", "code": "match = re.search(pattern, line)\nrecord = match.groupdict()\nprint(record[\"level\"])", "explanation": "groupdict возвращает словарь с именами групп."},
                    {"title": "Типизация", "code": "record[\"status\"] = \"500\"\nstatus = int(record[\"status\"])", "explanation": "После извлечения строки можно привести к нужному типу."},
                ],
                "exercise": {
                    "description": "Разберите access-log на ip, method, path и status через именованные группы.",
                    "starterCode": "import re\n\nline = \"10.0.0.5 POST /api/orders 201\"\n",
                    "hint": "Используйте (?P<name>...) для каждой части строки.",
                    "solution": "import re\n\nline = \"10.0.0.5 POST /api/orders 201\"\npattern = r\"(?P<ip>\\d+\\.\\d+\\.\\d+\\.\\d+) (?P<method>[A-Z]+) (?P<path>\\S+) (?P<status>\\d+)\"\nrecord = re.search(pattern, line).groupdict()\nrecord[\"status\"] = int(record[\"status\"])\nprint(record)",
                },
            },
            "backreferences": {
                "blocks": [
                    {"title": "Дубли слов", "code": "import re\ntext = \"retry retry failed\"\nmatch = re.search(r\"\\b(\\w+)\\s+\\1\\b\", text)", "explanation": "\\1 ссылается на текст, найденный первой группой."},
                    {"title": "Повтор id", "code": "line = \"id=42 previous=42\"\nsame = re.search(r\"id=(\\d+) previous=\\1\", line) is not None", "explanation": "Обратная ссылка проверяет повтор того же значения."},
                    {"title": "sub с группами", "code": "date = \"2026-08-02\"\npretty = re.sub(r\"(\\d{4})-(\\d{2})-(\\d{2})\", r\"\\3.\\2.\\1\", date)", "explanation": "В замене можно переставлять найденные группы."},
                ],
                "exercise": {
                    "description": "Найдите повторяющийся код ошибки и преобразуйте дату из YYYY-MM-DD в DD/MM/YYYY.",
                    "starterCode": "import re\n\nline = \"error=E42 retry=E42 date=2026-08-02\"\n",
                    "hint": "Для повторяющегося кода используйте \\1, для даты re.sub с тремя группами.",
                    "solution": "import re\n\nline = \"error=E42 retry=E42 date=2026-08-02\"\nhas_same_code = re.search(r\"error=(E\\d+) retry=\\1\", line) is not None\nconverted = re.sub(r\"(\\d{4})-(\\d{2})-(\\d{2})\", r\"\\3/\\2/\\1\", line)\nprint(has_same_code, converted)",
                },
            },
            "log-parsing": {
                "blocks": [
                    {"title": "Шаблон", "code": "import re\npattern = re.compile(r\"^(?P<ts>\\S+) (?P<level>\\w+) user=(?P<user>\\w+) status=(?P<status>\\d+)$\")", "explanation": "compile удобно использовать для повторного парсинга строк."},
                    {"title": "Одна строка", "code": "line = \"2026-08-02T10:15:00 ERROR user=alice status=500\"\nrecord = pattern.search(line).groupdict()", "explanation": "Именованные группы превращают лог в словарь."},
                    {"title": "Фильтр", "code": "record[\"status\"] = int(record[\"status\"])\nis_error = record[\"status\"] >= 500\nprint(is_error)", "explanation": "После парсинга можно фильтровать записи по числовым полям."},
                ],
                "exercise": {
                    "description": "Разберите несколько строк лога и оставьте только статусы 500 и выше.",
                    "starterCode": "import re\n\nlines = [\"10:00 INFO user=bob status=200\", \"10:01 ERROR user=alice status=503\"]\n",
                    "hint": "Скомпилируйте шаблон с named groups, затем преобразуйте status в int.",
                    "solution": "import re\n\nlines = [\"10:00 INFO user=bob status=200\", \"10:01 ERROR user=alice status=503\"]\npattern = re.compile(r\"^(?P<time>\\S+) (?P<level>\\w+) user=(?P<user>\\w+) status=(?P<status>\\d+)$\")\nrecords = [pattern.search(line).groupdict() for line in lines]\nerrors = [item for item in records if int(item[\"status\"]) >= 500]\nprint(errors)",
                },
            },
            "cleanup-pipelines": {
                "blocks": [
                    {"title": "Пробелы", "code": "import re\nraw = \"  Alice   Smith\\t<alice@example.com>  \"\ntext = re.sub(r\"\\s+\", \" \", raw.strip())", "explanation": "Первый шаг нормализует пробельные символы."},
                    {"title": "Извлечение email", "code": "email = re.search(r\"[\\w.-]+@[\\w.-]+\", text).group()\nname = re.sub(r\"\\s*<.*>$\", \"\", text)", "explanation": "Можно сочетать извлечение и удаление лишнего хвоста."},
                    {"title": "Slug", "code": "slug = re.sub(r\"[^a-z0-9]+\", \"-\", name.lower()).strip(\"-\")\nprint(slug, email)", "explanation": "Финальный sub приводит имя к машинному формату."},
                ],
                "exercise": {
                    "description": "Очистите контакт: нормализуйте пробелы, извлеките email и создайте slug из имени.",
                    "starterCode": "import re\n\nraw = \"  Bob   Stone   <bob.stone@example.com> \"\n",
                    "hint": "Сначала strip и \\s+, затем search для email и sub для slug.",
                    "solution": "import re\n\nraw = \"  Bob   Stone   <bob.stone@example.com> \"\ntext = re.sub(r\"\\s+\", \" \", raw.strip())\nemail = re.search(r\"[\\w.-]+@[\\w.-]+\", text).group()\nname = re.sub(r\"\\s*<.*>$\", \"\", text)\nslug = re.sub(r\"[^a-z0-9]+\", \"-\", name.lower()).strip(\"-\")\nprint(email, slug)",
                },
            },
        }

        fallback_by_difficulty = {
            "beginner": "regex-functions",
            "intermediate": "groups-extraction",
            "advanced": "log-parsing",
        }
        return snippets_by_topic.get(topic) or snippets_by_topic[fallback_by_difficulty.get(difficulty, "regex-functions")]

    def _terminal_snippets(self, library: str, topic: str, difficulty: str) -> dict[str, Any]:
        snippets_by_topic: dict[str, dict[str, Any]] = {
            "linux-basics": {
                "blocks": [
                    {"title": "Где я", "code": "pwd\nls -la", "explanation": "pwd показывает текущую директорию, ls -la выводит подробный список файлов."},
                    {"title": "Переходы", "code": "cd ~/projects\nmkdir logs\ncd logs", "explanation": "cd меняет директорию, mkdir создаёт папку для рабочих файлов."},
                    {"title": "Просмотр", "code": "cat app.log\nhead -20 app.log\ntail -20 app.log", "explanation": "cat, head и tail помогают быстро посмотреть содержимое файла."},
                ],
                "exercise": {
                    "description": "Создайте папку reports, перейдите в неё и посмотрите первые строки файла access.log.",
                    "starterCode": "pwd\n",
                    "hint": "Нужны mkdir, cd и head.",
                    "solution": "pwd\nmkdir reports\ncd reports\nhead -20 access.log",
                },
            },
            "files-directories": {
                "blocks": [
                    {"title": "Поиск файлов", "code": "find . -maxdepth 2 -type f -name \"*.log\"", "explanation": "find ищет файлы по глубине, типу и маске имени."},
                    {"title": "Копирование", "code": "mkdir -p archive\ncp app.log archive/app.log", "explanation": "mkdir -p готовит директорию, cp копирует файл."},
                    {"title": "Проверка размера", "code": "ls -lh archive\ndu -sh archive", "explanation": "ls -lh и du -sh показывают размер файлов и директории."},
                ],
                "exercise": {
                    "description": "Найдите JSON-файлы на глубине 2, скопируйте config.json в backup и проверьте размер backup.",
                    "starterCode": "find . -maxdepth 2 -type f -name \"*.json\"\n",
                    "hint": "Используйте mkdir -p, cp и du -sh.",
                    "solution": "find . -maxdepth 2 -type f -name \"*.json\"\nmkdir -p backup\ncp config.json backup/config.json\ndu -sh backup",
                },
            },
            "pipes-grep-redirection": {
                "blocks": [
                    {"title": "grep", "code": "grep \"ERROR\" app.log\ngrep -n \"timeout\" app.log", "explanation": "grep ищет строки, -n добавляет номера строк."},
                    {"title": "pipe", "code": "cat app.log | grep \"ERROR\" | head -10", "explanation": "pipe передаёт вывод одной команды на вход следующей."},
                    {"title": "redirect", "code": "grep \"ERROR\" app.log > errors.log\nwc -l errors.log", "explanation": "> сохраняет результат в файл, wc -l считает строки."},
                ],
                "exercise": {
                    "description": "Найдите WARN-строки в service.log, сохраните их и посчитайте количество.",
                    "starterCode": "grep \"WARN\" service.log\n",
                    "hint": "Используйте > для сохранения и wc -l для подсчёта.",
                    "solution": "grep \"WARN\" service.log > warnings.log\nwc -l warnings.log\nhead -5 warnings.log",
                },
            },
            "permissions-processes": {
                "blocks": [
                    {"title": "Права", "code": "ls -l scripts\nchmod u+x scripts/run.sh", "explanation": "ls -l показывает права, chmod u+x добавляет запуск владельцу."},
                    {"title": "Процессы", "code": "ps aux | grep \"worker\"\npgrep -fl \"worker\"", "explanation": "ps и pgrep помогают найти процессы по имени."},
                    {"title": "Окружение", "code": "env | sort | grep \"APP_\"\nwhich python", "explanation": "env показывает переменные, which помогает понять путь к бинарнику."},
                ],
                "exercise": {
                    "description": "Сделайте scripts/check.sh исполняемым, найдите процессы api и путь к uvicorn.",
                    "starterCode": "ls -l scripts\n",
                    "hint": "Нужны chmod u+x, pgrep -fl и which.",
                    "solution": "ls -l scripts\nchmod u+x scripts/check.sh\npgrep -fl \"api\"\nwhich uvicorn",
                },
            },
            "system-diagnostics": {
                "blocks": [
                    {"title": "Процессы", "code": "ps aux | grep \"uvicorn\"\npgrep -fl \"python\"", "explanation": "ps и pgrep помогают найти запущенные процессы по имени."},
                    {"title": "Диск", "code": "df -h\ndu -sh logs", "explanation": "df показывает свободное место, du оценивает размер директории."},
                    {"title": "Сеть", "code": "curl -I http://127.0.0.1:8000/health\nss -ltn", "explanation": "curl проверяет HTTP-ответ, ss показывает слушающие TCP-порты."},
                ],
                "exercise": {
                    "description": "Проверьте место на диске, найдите python-процессы и убедитесь, что health endpoint отвечает.",
                    "starterCode": "df -h\n",
                    "hint": "Комбинируйте df, pgrep и curl -I.",
                    "solution": "df -h\npgrep -fl \"python\"\ncurl -I http://127.0.0.1:8000/health",
                },
            },
            "logs-journals": {
                "blocks": [
                    {"title": "Последние строки", "code": "tail -100 app.log\ntail -f app.log", "explanation": "tail показывает конец файла и может следить за обновлениями."},
                    {"title": "Фильтрация", "code": "grep -n \"ERROR\" app.log | tail -20", "explanation": "grep с pipe помогает быстро сузить лог до нужных событий."},
                    {"title": "systemd logs", "code": "journalctl -u app.service --since \"1 hour ago\"\njournalctl -u app.service -n 50", "explanation": "journalctl читает журналы systemd-сервисов."},
                ],
                "exercise": {
                    "description": "Покажите последние ERROR из app.log и последние 50 строк журнала nginx.service.",
                    "starterCode": "tail -100 app.log\n",
                    "hint": "Комбинируйте grep, tail и journalctl -n.",
                    "solution": "tail -100 app.log\ngrep -n \"ERROR\" app.log | tail -20\njournalctl -u nginx.service -n 50",
                },
            },
            "git-basics": {
                "blocks": [
                    {"title": "Статус", "code": "git status\ngit diff -- README.md", "explanation": "status показывает состояние рабочей копии, diff показывает изменения."},
                    {"title": "Индекс", "code": "git add README.md\ngit status --short", "explanation": "git add переносит выбранный файл в индекс."},
                    {"title": "Коммит", "code": "git commit -m \"docs: update readme\"\ngit log --oneline -5", "explanation": "commit фиксирует индекс, log показывает последние коммиты."},
                ],
                "exercise": {
                    "description": "Проверьте изменения, добавьте файл notes.md и создайте короткий коммит.",
                    "starterCode": "git status --short\n",
                    "hint": "Последовательность: status, diff, add, commit.",
                    "solution": "git status --short\ngit diff -- notes.md\ngit add notes.md\ngit commit -m \"docs: update notes\"",
                },
            },
            "git-diff-staging": {
                "blocks": [
                    {"title": "Рабочий diff", "code": "git diff\ngit diff -- app.py", "explanation": "git diff показывает незастейдженные изменения."},
                    {"title": "Staged diff", "code": "git add app.py\ngit diff --cached", "explanation": "git diff --cached показывает то, что попадёт в коммит."},
                    {"title": "Частичный add", "code": "git add -p app.py\ngit status --short", "explanation": "git add -p позволяет выбрать отдельные hunks."},
                ],
                "exercise": {
                    "description": "Проверьте изменения в app.py, добавьте их частично и посмотрите staged diff.",
                    "starterCode": "git diff -- app.py\n",
                    "hint": "Используйте git add -p и git diff --cached.",
                    "solution": "git diff -- app.py\ngit add -p app.py\ngit diff --cached\ngit status --short",
                },
            },
            "git-branches-remotes": {
                "blocks": [
                    {"title": "Ветка", "code": "git switch -c feature/terminal-lessons\ngit branch --show-current", "explanation": "switch -c создаёт и сразу включает новую ветку."},
                    {"title": "Синхронизация", "code": "git fetch origin\ngit status -sb", "explanation": "fetch забирает данные с remote без изменения рабочей ветки."},
                    {"title": "Публикация", "code": "git push -u origin feature/terminal-lessons", "explanation": "-u связывает локальную ветку с удалённой."},
                ],
                "exercise": {
                    "description": "Создайте ветку feature/git-practice, проверьте upstream и подготовьте push.",
                    "starterCode": "git fetch origin\n",
                    "hint": "Нужны switch -c, status -sb и push -u.",
                    "solution": "git fetch origin\ngit switch -c feature/git-practice\ngit status -sb\ngit push -u origin feature/git-practice",
                },
            },
            "git-merge-conflicts": {
                "blocks": [
                    {"title": "Подготовка", "code": "git fetch origin\ngit switch feature/api", "explanation": "Перед merge стоит обновить remote refs и перейти в рабочую ветку."},
                    {"title": "Merge", "code": "git merge origin/main\ngit status --short", "explanation": "merge подтягивает изменения main и status показывает конфликты."},
                    {"title": "Разрешение", "code": "git add backend/app.py\ngit commit -m \"fix: resolve api merge\"", "explanation": "После ручного исправления конфликтный файл добавляют и завершают merge-коммит."},
                ],
                "exercise": {
                    "description": "Слейте origin/main в feature/auth и завершите конфликт в auth.py.",
                    "starterCode": "git fetch origin\n",
                    "hint": "Последовательность: switch, merge, status, add, commit.",
                    "solution": "git fetch origin\ngit switch feature/auth\ngit merge origin/main\ngit status --short\ngit add auth.py\ngit commit -m \"fix: resolve auth merge\"",
                },
            },
            "git-history-recovery": {
                "blocks": [
                    {"title": "История", "code": "git log --oneline --decorate -10\ngit show --stat HEAD", "explanation": "log и show помогают понять последние изменения."},
                    {"title": "Поиск", "code": "git reflog --date=relative\ngit diff HEAD~1..HEAD", "explanation": "reflog показывает перемещения HEAD, diff сравнивает состояния."},
                    {"title": "Точный откат файла", "code": "git restore --source=HEAD~1 -- README.md\ngit diff -- README.md", "explanation": "restore для конкретного файла безопаснее полного сброса ветки."},
                ],
                "exercise": {
                    "description": "Найдите последний коммит, посмотрите изменения и восстановите только docs/guide.md из предыдущего коммита.",
                    "starterCode": "git log --oneline -5\n",
                    "hint": "Используйте show, diff и restore --source для одного файла.",
                    "solution": "git log --oneline -5\ngit show --stat HEAD\ngit diff HEAD~1..HEAD -- docs/guide.md\ngit restore --source=HEAD~1 -- docs/guide.md",
                },
            },
            "git-stash-bisect": {
                "blocks": [
                    {"title": "Stash", "code": "git status --short\ngit stash push -m \"wip api debug\"", "explanation": "stash временно сохраняет незавершённые изменения."},
                    {"title": "Возврат", "code": "git stash list\ngit stash show --stat stash@{0}", "explanation": "list и show помогают выбрать нужный stash."},
                    {"title": "Bisect", "code": "git bisect start\ngit bisect bad\ngit bisect good v1.2.0", "explanation": "bisect запускает бинарный поиск коммита, который внёс регрессию."},
                ],
                "exercise": {
                    "description": "Сохраните WIP-изменения, посмотрите stash и начните bisect между HEAD и v1.0.0.",
                    "starterCode": "git status --short\n",
                    "hint": "Используйте stash push, stash list и git bisect.",
                    "solution": "git status --short\ngit stash push -m \"wip terminal practice\"\ngit stash list\ngit bisect start\ngit bisect bad\ngit bisect good v1.0.0",
                },
            },
            "conda-basics": {
                "blocks": [
                    {"title": "Версия", "code": "conda --version\nconda info", "explanation": "Эти команды проверяют установку и базовую конфигурацию conda."},
                    {"title": "Окружения", "code": "conda env list\nconda activate data-lab", "explanation": "env list показывает окружения, activate включает выбранное."},
                    {"title": "Пакеты", "code": "conda list\nconda list pandas", "explanation": "conda list показывает установленные пакеты."},
                ],
                "exercise": {
                    "description": "Проверьте conda, найдите окружения и убедитесь, что numpy установлен в активном окружении.",
                    "starterCode": "conda --version\n",
                    "hint": "Нужны conda env list и conda list.",
                    "solution": "conda --version\nconda env list\nconda list numpy",
                },
            },
            "conda-package-search": {
                "blocks": [
                    {"title": "Поиск", "code": "conda search pandas\nconda search \"numpy>=1.26\"", "explanation": "conda search помогает найти доступные версии пакетов."},
                    {"title": "Информация", "code": "conda info pandas\nconda list --explicit", "explanation": "info и list --explicit полезны для диагностики пакетов."},
                    {"title": "Проверка канала", "code": "conda config --show channels\nconda config --show channel_priority", "explanation": "Порядок каналов влияет на выбор сборок."},
                ],
                "exercise": {
                    "description": "Найдите версии scipy, проверьте каналы и покажите явно установленные пакеты.",
                    "starterCode": "conda search scipy\n",
                    "hint": "Добавьте config --show channels и list --explicit.",
                    "solution": "conda search scipy\nconda config --show channels\nconda config --show channel_priority\nconda list --explicit",
                },
            },
            "conda-project-envs": {
                "blocks": [
                    {"title": "Создание", "code": "conda create -n ml-lab python=3.12\nconda activate ml-lab", "explanation": "create создаёт изолированное окружение с нужной версией Python."},
                    {"title": "Установка", "code": "conda install pandas scikit-learn\nconda list scikit-learn", "explanation": "install добавляет пакеты в активное окружение."},
                    {"title": "Экспорт", "code": "conda env export --from-history > environment.yml\ncat environment.yml", "explanation": "--from-history сохраняет явно установленные зависимости."},
                ],
                "exercise": {
                    "description": "Создайте окружение api-lab с Python 3.12, установите fastapi и экспортируйте environment.yml.",
                    "starterCode": "conda create -n api-lab python=3.12\n",
                    "hint": "После activate используйте conda install и env export --from-history.",
                    "solution": "conda create -n api-lab python=3.12\nconda activate api-lab\nconda install fastapi uvicorn\nconda env export --from-history > environment.yml",
                },
            },
            "conda-channels-priority": {
                "blocks": [
                    {"title": "Каналы", "code": "conda config --show channels\nconda config --add channels conda-forge", "explanation": "channels задают источники пакетов."},
                    {"title": "Приоритет", "code": "conda config --set channel_priority strict\nconda config --show channel_priority", "explanation": "strict priority снижает риск смешивания несовместимых сборок."},
                    {"title": "Установка", "code": "conda install -c conda-forge httpx\nconda list httpx", "explanation": "-c явно выбирает канал для установки пакета."},
                ],
                "exercise": {
                    "description": "Добавьте conda-forge, включите strict priority и установите python-dotenv из conda-forge.",
                    "starterCode": "conda config --show channels\n",
                    "hint": "Нужны config --add, config --set и install -c.",
                    "solution": "conda config --add channels conda-forge\nconda config --set channel_priority strict\nconda install -c conda-forge python-dotenv\nconda list python-dotenv",
                },
            },
            "conda-reproducibility": {
                "blocks": [
                    {"title": "Файл окружения", "code": "conda env export --from-history > environment.yml\ngit diff -- environment.yml", "explanation": "environment.yml фиксирует зависимости проекта."},
                    {"title": "Воссоздание", "code": "conda env create -f environment.yml\nconda activate project-env", "explanation": "env create поднимает окружение из файла."},
                    {"title": "Обновление", "code": "conda env update -f environment.yml --prune\nconda list", "explanation": "--prune убирает пакеты, которых больше нет в файле."},
                ],
                "exercise": {
                    "description": "Экспортируйте минимальный environment.yml и покажите команды для воссоздания и обновления окружения.",
                    "starterCode": "conda env export --from-history > environment.yml\n",
                    "hint": "Нужны env create и env update --prune.",
                    "solution": "conda env export --from-history > environment.yml\nconda env create -f environment.yml\nconda env update -f environment.yml --prune\nconda list",
                },
            },
            "conda-troubleshooting": {
                "blocks": [
                    {"title": "Информация", "code": "conda info\nconda env list", "explanation": "Базовая диагностика начинается с версии, каналов и списка окружений."},
                    {"title": "Проверка пакета", "code": "conda list pandas\npython -c \"import pandas; print(pandas.__version__)\"", "explanation": "Важно сверять пакет в conda и импорт в активном Python."},
                    {"title": "Обновление metadata", "code": "conda update conda\nconda clean --index-cache", "explanation": "Обновление conda и очистка index cache помогают при проблемах resolver."},
                ],
                "exercise": {
                    "description": "Проверьте активное окружение, версию numpy при импорте и очистите index cache.",
                    "starterCode": "conda info\n",
                    "hint": "Используйте conda env list, conda list и python -c.",
                    "solution": "conda info\nconda env list\nconda list numpy\npython -c \"import numpy; print(numpy.__version__)\"\nconda clean --index-cache",
                },
            },
            "docker-basics": {
                "blocks": [
                    {"title": "Версия", "code": "docker --version\ndocker info", "explanation": "Проверяет клиент Docker и доступность daemon."},
                    {"title": "Контейнер", "code": "docker run --name web-demo -p 8080:80 nginx:alpine", "explanation": "run создаёт контейнер из образа и публикует порт."},
                    {"title": "Наблюдение", "code": "docker ps\ndocker logs web-demo", "explanation": "ps показывает контейнеры, logs выводит журнал контейнера."},
                ],
                "exercise": {
                    "description": "Запустите nginx-контейнер с именем docs-web, проверьте список контейнеров и логи.",
                    "starterCode": "docker --version\n",
                    "hint": "Используйте docker run --name, затем ps и logs.",
                    "solution": "docker --version\ndocker run --name docs-web -p 8080:80 nginx:alpine\ndocker ps\ndocker logs docs-web",
                },
            },
            "docker-images": {
                "blocks": [
                    {"title": "Список", "code": "docker image ls\ndocker image ls nginx", "explanation": "image ls показывает локальные образы и их теги."},
                    {"title": "Pull", "code": "docker pull nginx:alpine\ndocker image inspect nginx:alpine", "explanation": "pull скачивает образ, inspect показывает metadata."},
                    {"title": "History", "code": "docker image history nginx:alpine", "explanation": "history показывает слои образа."},
                ],
                "exercise": {
                    "description": "Скачайте redis:alpine, проверьте образ и посмотрите его слои.",
                    "starterCode": "docker image ls\n",
                    "hint": "Нужны docker pull, image inspect и image history.",
                    "solution": "docker image ls\ndocker pull redis:alpine\ndocker image inspect redis:alpine\ndocker image history redis:alpine",
                },
            },
            "docker-compose": {
                "blocks": [
                    {"title": "Статус", "code": "docker compose ps\ndocker compose config", "explanation": "ps показывает сервисы, config проверяет итоговую конфигурацию compose."},
                    {"title": "Запуск", "code": "docker compose up -d --build\ndocker compose logs -f backend", "explanation": "up -d запускает сервисы в фоне, logs помогает смотреть backend."},
                    {"title": "Проверка", "code": "docker compose exec backend python -V\ncurl -I http://127.0.0.1:3000", "explanation": "exec запускает команду внутри сервиса, curl проверяет frontend."},
                ],
                "exercise": {
                    "description": "Пересоберите backend и frontend, проверьте статус сервисов и последние backend-логи.",
                    "starterCode": "docker compose ps\n",
                    "hint": "Нужны up -d --build, ps и logs.",
                    "solution": "docker compose up -d --build backend frontend\ndocker compose ps\ndocker compose logs --tail=80 backend",
                },
            },
            "docker-volumes-networks": {
                "blocks": [
                    {"title": "Volumes", "code": "docker volume ls\ndocker volume inspect postgres-data", "explanation": "volume ls и inspect помогают понять, где хранятся данные."},
                    {"title": "Networks", "code": "docker network ls\ndocker network inspect app_default", "explanation": "network inspect показывает контейнеры и настройки сети."},
                    {"title": "Compose resources", "code": "docker compose ps\ndocker compose exec backend hostname", "explanation": "compose exec помогает проверять сеть изнутри сервиса."},
                ],
                "exercise": {
                    "description": "Проверьте volume postgres-data, сеть app_default и hostname backend-сервиса.",
                    "starterCode": "docker volume ls\n",
                    "hint": "Используйте volume inspect, network inspect и compose exec.",
                    "solution": "docker volume inspect postgres-data\ndocker network inspect app_default\ndocker compose exec backend hostname",
                },
            },
            "docker-debug-build": {
                "blocks": [
                    {"title": "Слои", "code": "docker build --progress=plain -t cla-backend ./backend", "explanation": "--progress=plain делает лог сборки подробным и пригодным для диагностики."},
                    {"title": "Inspect", "code": "docker inspect cla-backend\ndocker image history cla-backend", "explanation": "inspect и history помогают разобраться с образом."},
                    {"title": "Exec", "code": "docker compose exec backend env\ndocker compose exec backend python -m pytest", "explanation": "exec полезен для диагностики окружения внутри контейнера."},
                ],
                "exercise": {
                    "description": "Соберите backend-образ с подробным логом, посмотрите историю образа и проверьте переменные контейнера.",
                    "starterCode": "docker build --progress=plain -t cla-backend ./backend\n",
                    "hint": "Добавьте image history и compose exec env.",
                    "solution": "docker build --progress=plain -t cla-backend ./backend\ndocker image history cla-backend\ndocker compose exec backend env",
                },
            },
            "docker-production-diagnostics": {
                "blocks": [
                    {"title": "Health", "code": "docker compose ps\ncurl -I http://127.0.0.1:3000", "explanation": "Проверяет статус compose-сервисов и HTTP-доступность frontend."},
                    {"title": "Logs", "code": "docker compose logs --tail=120 backend\ndocker compose logs --tail=120 frontend", "explanation": "Свежие логи backend и frontend обычно быстрее всего показывают причину сбоя."},
                    {"title": "Env", "code": "docker compose exec backend printenv\ndocker compose exec frontend printenv", "explanation": "printenv внутри контейнера проверяет фактические переменные окружения."},
                ],
                "exercise": {
                    "description": "Проверьте compose-статус, последние backend-логи и переменные backend-контейнера.",
                    "starterCode": "docker compose ps\n",
                    "hint": "Добавьте logs --tail и compose exec backend printenv.",
                    "solution": "docker compose ps\ndocker compose logs --tail=120 backend\ndocker compose exec backend printenv",
                },
            },
        }

        fallback_by_library = {
            "linux": {"beginner": "linux-basics", "intermediate": "pipes-grep-redirection", "advanced": "system-diagnostics"},
            "git": {"beginner": "git-basics", "intermediate": "git-branches-remotes", "advanced": "git-history-recovery"},
            "conda": {"beginner": "conda-basics", "intermediate": "conda-project-envs", "advanced": "conda-reproducibility"},
            "docker": {"beginner": "docker-basics", "intermediate": "docker-compose", "advanced": "docker-debug-build"},
        }
        fallback_topic = fallback_by_library.get(library, {}).get(difficulty, "linux-basics")
        return snippets_by_topic.get(topic) or snippets_by_topic[fallback_topic]
