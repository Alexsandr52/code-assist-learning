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


def test_create_generic_fallback_practice_session():
    response = client.post(
        "/api/practice-sessions",
        json={
            "language": "python",
            "library": "pandas",
            "topic": "select-columns",
            "difficulty": "beginner",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["source"] == "fallback"
    assert payload["library"] == "pandas"
    assert payload["topic"] == "select-columns"
    assert payload["blocks"][0]["code"] == "import pandas as pd"
