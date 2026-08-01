from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_catalog_languages():
    response = client.get("/api/languages")
    assert response.status_code == 200
    assert response.json()[0]["slug"] == "python"


def test_create_fallback_practice_session():
    response = client.post(
        "/api/practice-sessions",
        json={
            "language": "python",
            "library": "requests",
            "topic": "get-requests",
            "difficulty": "beginner",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["sessionId"].startswith("session_")
    assert payload["source"] == "fallback"
    assert len(payload["blocks"]) >= 3

