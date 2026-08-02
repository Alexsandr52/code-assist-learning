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
    slugs = {item["slug"] for item in response.json()}
    assert "python" in slugs
    assert "terminal" in slugs


def test_catalog_includes_re_library_and_topics():
    libraries_response = client.get("/api/libraries?language=python")
    assert libraries_response.status_code == 200
    assert any(item["slug"] == "re" for item in libraries_response.json())

    topics_response = client.get("/api/topics?library=re&difficulty=advanced")
    assert topics_response.status_code == 200
    topics = topics_response.json()
    assert any(item["slug"] == "log-parsing" for item in topics)
    assert any(item["slug"] == "cleanup-pipelines" for item in topics)


def test_catalog_includes_terminal_libraries_and_topics():
    libraries_response = client.get("/api/libraries?language=terminal")
    assert libraries_response.status_code == 200
    library_slugs = {item["slug"] for item in libraries_response.json()}
    assert {"linux", "git", "conda", "docker"}.issubset(library_slugs)

    topics_response = client.get("/api/topics?library=git&difficulty=advanced")
    assert topics_response.status_code == 200
    assert any(item["slug"] == "git-history-recovery" for item in topics_response.json())


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


def test_pandas_advanced_fallback_matches_selected_topic():
    response = client.post(
        "/api/practice-sessions",
        json={
            "language": "python",
            "library": "pandas",
            "topic": "rolling-window",
            "difficulty": "advanced",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    all_code = "\n".join(block["code"] for block in payload["blocks"])
    assert payload["source"] == "fallback"
    assert payload["library"] == "pandas"
    assert payload["topic"] == "rolling-window"
    assert payload["difficulty"] == "advanced"
    assert "rolling" in all_code
    assert "DataFrame({\"name\"" not in all_code


def test_re_advanced_fallback_matches_selected_topic():
    response = client.post(
        "/api/practice-sessions",
        json={
            "language": "python",
            "library": "re",
            "topic": "log-parsing",
            "difficulty": "advanced",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    all_code = "\n".join(block["code"] for block in payload["blocks"])
    assert payload["source"] == "fallback"
    assert payload["library"] == "re"
    assert payload["topic"] == "log-parsing"
    assert payload["difficulty"] == "advanced"
    assert "import re" in all_code
    assert "groupdict" in all_code


def test_terminal_git_fallback_matches_selected_topic():
    response = client.post(
        "/api/practice-sessions",
        json={
            "language": "terminal",
            "library": "git",
            "topic": "git-branches-remotes",
            "difficulty": "intermediate",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    all_code = "\n".join(block["code"] for block in payload["blocks"])
    assert payload["source"] == "fallback"
    assert payload["language"] == "terminal"
    assert payload["library"] == "git"
    assert payload["topic"] == "git-branches-remotes"
    assert "git switch -c" in all_code
    assert "git push -u" in all_code
