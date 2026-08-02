import asyncio

from app.core.config import Settings
from app.schemas.practice import PracticeSessionCreate
from app.services.content_service import ContentService


class FakeRedis:
    def __init__(self) -> None:
        self.setex_calls: list[tuple[str, int, str]] = []

    def get(self, key: str) -> None:
        return None

    def setex(self, key: str, ttl: int, value: str) -> None:
        self.setex_calls.append((key, ttl, value))


def test_generic_fallback_is_not_cached():
    settings = Settings(
        database_url=None,
        redis_url=None,
        yandex_gpt_endpoint=None,
        yandex_gpt_api_key=None,
        yandex_gpt_model=None,
    )
    service = ContentService(settings=settings, db=None)
    fake_redis = FakeRedis()
    service.redis = fake_redis
    payload = PracticeSessionCreate(
        language="python",
        library="pandas",
        topic="rolling-window",
        difficulty="advanced",
    )

    content, source = asyncio.run(service._get_content(payload, variant=1))

    assert source == "fallback"
    assert content.topic == "rolling-window"
    assert fake_redis.setex_calls == []
