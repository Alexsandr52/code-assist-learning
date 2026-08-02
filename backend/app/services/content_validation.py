import ast
import re

from pydantic import ValidationError
from app.schemas.content import LearningContentPayload


CYRILLIC_RE = re.compile(r"[А-Яа-яЁё]")


def validate_learning_content(raw: dict) -> LearningContentPayload:
    try:
        content = LearningContentPayload.model_validate(raw)
    except ValidationError as exc:
        raise ValueError(str(exc)) from exc

    for block in content.blocks:
        if len(block.code.splitlines()) > 12:
            raise ValueError("code block has too many lines")
        _validate_python_code(block.code)
    _validate_python_code(content.exercise.starterCode)
    _validate_python_code(content.exercise.solution)
    return content


def _validate_python_code(code: str) -> None:
    if CYRILLIC_RE.search(code):
        raise ValueError("code contains cyrillic characters")
    try:
        ast.parse(code or "\n")
    except SyntaxError as exc:
        raise ValueError(f"code contains invalid Python syntax: {exc.msg}") from exc
