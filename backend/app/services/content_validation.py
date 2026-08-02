import ast
import re

from pydantic import ValidationError
from app.schemas.content import LearningContentPayload


CYRILLIC_RE = re.compile(r"[А-Яа-яЁё]")
SHELL_LANGUAGES = {"terminal", "bash", "shell"}
DENIED_SHELL_TOKENS = (
    "sudo ",
    "rm ",
    "rm\t",
    "rm -",
    "rm -rf",
    "mkfs",
    "dd if=",
    ":(){",
    "shutdown",
    "reboot",
    "curl | sh",
    "wget | sh",
    "docker system prune",
    "docker rm -f",
    "git reset --hard",
    "> /dev/sd",
)


def validate_learning_content(raw: dict) -> LearningContentPayload:
    try:
        content = LearningContentPayload.model_validate(raw)
    except ValidationError as exc:
        raise ValueError(str(exc)) from exc

    for block in content.blocks:
        if len(block.code.splitlines()) > 12:
            raise ValueError("code block has too many lines")
        _validate_code(content.language, block.code)
    _validate_code(content.language, content.exercise.starterCode)
    _validate_code(content.language, content.exercise.solution)
    return content


def _validate_code(language: str, code: str) -> None:
    if language in SHELL_LANGUAGES:
        _validate_shell_code(code)
        return
    _validate_python_code(code)


def _validate_python_code(code: str) -> None:
    if CYRILLIC_RE.search(code):
        raise ValueError("code contains cyrillic characters")
    try:
        ast.parse(code or "\n")
    except SyntaxError as exc:
        raise ValueError(f"code contains invalid Python syntax: {exc.msg}") from exc


def _validate_shell_code(code: str) -> None:
    lowered = code.lower()
    if any(token in lowered for token in DENIED_SHELL_TOKENS):
        raise ValueError("shell command contains a denied construct")
    if CYRILLIC_RE.search(code):
        raise ValueError("shell command contains cyrillic characters")
