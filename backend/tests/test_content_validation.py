import pytest
from app.services.content_validation import validate_learning_content


VALID_CONTENT = {
    "language": "python",
    "library": "requests",
    "topic": "GET-запросы",
    "difficulty": "beginner",
    "blocks": [
        {"title": "Импорт", "code": "import requests", "explanation": "Импортирует библиотеку."},
        {"title": "Запрос", "code": "response = requests.get(\"https://example.com\")", "explanation": "Отправляет запрос."},
        {"title": "Печать", "code": "print(response.status_code)", "explanation": "Печатает код ответа."},
    ],
    "exercise": {
        "description": "Отправьте запрос.",
        "starterCode": "import requests\n\n",
        "hint": "Используйте requests.get.",
        "solution": "import requests\n\nresponse = requests.get(\"https://example.com\")\nprint(response.status_code)",
    },
}


def test_valid_content_passes():
    content = validate_learning_content(VALID_CONTENT)
    assert content.language == "python"
    assert len(content.blocks) == 3


def test_rejects_too_few_blocks():
    raw = {**VALID_CONTENT, "blocks": VALID_CONTENT["blocks"][:2]}
    with pytest.raises(ValueError):
        validate_learning_content(raw)


def test_rejects_dangerous_code():
    raw = {
        **VALID_CONTENT,
        "blocks": [
            *VALID_CONTENT["blocks"][:2],
            {"title": "Опасно", "code": "import os\nos.remove(\"data.txt\")", "explanation": "Опасный пример."},
        ],
    }
    with pytest.raises(ValueError):
        validate_learning_content(raw)

