import pytest
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


@pytest.mark.parametrize("library", ["linux", "git", "conda", "docker"])
@pytest.mark.parametrize("difficulty", ["beginner", "intermediate", "advanced"])
def test_terminal_catalog_has_multiple_topics_per_level(library, difficulty):
    response = client.get(f"/api/topics?library={library}&difficulty={difficulty}")
    assert response.status_code == 200
    assert len(response.json()) >= 2


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


@pytest.mark.parametrize(
    ("library", "topic", "difficulty"),
    [
        ("linux", "files-directories", "beginner"),
        ("linux", "permissions-processes", "intermediate"),
        ("linux", "logs-journals", "advanced"),
        ("git", "git-diff-staging", "beginner"),
        ("git", "git-merge-conflicts", "intermediate"),
        ("git", "git-stash-bisect", "advanced"),
        ("conda", "conda-package-search", "beginner"),
        ("conda", "conda-channels-priority", "intermediate"),
        ("conda", "conda-troubleshooting", "advanced"),
        ("docker", "docker-images", "beginner"),
        ("docker", "docker-volumes-networks", "intermediate"),
        ("docker", "docker-production-diagnostics", "advanced"),
    ],
)
def test_new_terminal_fallback_topics_match_selection(library, topic, difficulty):
    response = client.post(
        "/api/practice-sessions",
        json={
            "language": "terminal",
            "library": library,
            "topic": topic,
            "difficulty": difficulty,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["source"] == "fallback"
    assert payload["library"] == library
    assert payload["topic"] == topic
    assert payload["difficulty"] == difficulty
    assert len(payload["blocks"]) >= 3
