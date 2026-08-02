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


def test_rejects_invalid_python_syntax():
    raw = {
        **VALID_CONTENT,
        "blocks": [
            *VALID_CONTENT["blocks"][:2],
            {"title": "Синтаксис", "code": "if True print(\"ok\")", "explanation": "Некорректный Python."},
        ],
    }
    with pytest.raises(ValueError):
        validate_learning_content(raw)


def test_rejects_cyrillic_in_code():
    raw = {
        **VALID_CONTENT,
        "blocks": [
            *VALID_CONTENT["blocks"][:2],
            {"title": "Кириллица", "code": "дни = [\"Пн\", \"Вт\"]\nprint(дни)", "explanation": "Кириллические идентификаторы."},
        ],
    }
    with pytest.raises(ValueError):
        validate_learning_content(raw)


def test_accepts_terminal_shell_commands():
    raw = {
        **VALID_CONTENT,
        "language": "terminal",
        "library": "git",
        "topic": "git-basics",
        "blocks": [
            {"title": "Status", "code": "git status\ngit diff -- README.md", "explanation": "Проверяет изменения."},
            {"title": "Stage", "code": "git add README.md\ngit status --short", "explanation": "Добавляет файл в индекс."},
            {"title": "Log", "code": "git log --oneline -5", "explanation": "Показывает историю."},
        ],
        "exercise": {
            "description": "Проверьте статус.",
            "starterCode": "git status\n",
            "hint": "Используйте git status.",
            "solution": "git status\ngit diff -- README.md",
        },
    }

    content = validate_learning_content(raw)
    assert content.language == "terminal"


def test_rejects_destructive_shell_commands():
    raw = {
        **VALID_CONTENT,
        "language": "terminal",
        "library": "linux",
        "topic": "danger",
        "blocks": [
            {"title": "Safe", "code": "pwd", "explanation": "Показывает директорию."},
            {"title": "Also safe", "code": "ls -la", "explanation": "Показывает файлы."},
            {"title": "Danger", "code": "rm -rf build", "explanation": "Опасная команда."},
        ],
        "exercise": {
            "description": "Проверьте директорию.",
            "starterCode": "pwd\n",
            "hint": "Используйте pwd.",
            "solution": "pwd",
        },
    }

    with pytest.raises(ValueError):
        validate_learning_content(raw)
