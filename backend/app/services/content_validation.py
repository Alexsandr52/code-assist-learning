from pydantic import ValidationError
from app.schemas.content import LearningContentPayload


def validate_learning_content(raw: dict) -> LearningContentPayload:
    try:
        content = LearningContentPayload.model_validate(raw)
    except ValidationError as exc:
        raise ValueError(str(exc)) from exc

    for block in content.blocks:
        if len(block.code.splitlines()) > 12:
            raise ValueError("code block has too many lines")
    return content

