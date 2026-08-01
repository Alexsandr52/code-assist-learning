import json
import secrets
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


class PracticeSessionStore:
    def __init__(self) -> None:
        self.sessions: dict[str, PracticeSessionOut] = {}
        self.completed: dict[str, dict[str, Any]] = {}


session_store = PracticeSessionStore()

AUTO_VARIANT_COUNT = 24


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
        cache_key = self._cache_key(payload, variant)
        cached = self._read_cache(cache_key)
        if cached:
            return cached, "cache"

        persisted = self._read_database(cache_key)
        if persisted:
            self._write_cache(cache_key, persisted)
            return persisted, "database"

        fallback = self._load_fallback(payload)
        if self._generation_configured():
            generated = await self._try_generate(payload, cache_key, variant)
            if generated:
                return generated, "generated"

        if fallback:
            self._write_cache(cache_key, fallback)
            return fallback, "fallback"
        raise YandexGPTUnavailable("no generated or fallback content is available")

    async def _try_generate(self, payload: PracticeSessionCreate, cache_key: str, variant: int) -> LearningContentPayload | None:
        lock_key = f"lock:{cache_key}"
        lock_acquired = self._acquire_lock(lock_key)
        if not lock_acquired:
            return self._read_cache(cache_key)
        try:
            for _ in range(self.settings.max_generation_attempts):
                try:
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
                    return content
                except Exception:
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
            "requests_get_requests_beginner.json",
        ]
        base = Path(__file__).resolve().parents[1] / "fallback_content"
        for filename in candidates:
            path = base / filename
            if path.exists():
                return validate_learning_content(json.loads(path.read_text(encoding="utf-8")))
        return None
