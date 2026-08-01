from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator


Difficulty = Literal["beginner", "intermediate", "advanced"]
ContentStatus = Literal["generated", "validated", "published", "rejected"]
ContentSource = Literal["cache", "database", "generated", "fallback"]


class CodeBlock(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    code: str = Field(min_length=1, max_length=600)
    explanation: str = Field(min_length=1, max_length=800)

    @field_validator("code")
    @classmethod
    def reject_suspicious_code(cls, value: str) -> str:
        lowered = value.lower()
        denied = (
            "os.remove",
            "shutil.rmtree",
            "subprocess",
            "eval(",
            "exec(",
            "open(",
            "__import__",
            "input(",
            "pip install",
        )
        if any(token in lowered for token in denied):
            raise ValueError("code block contains a denied construct")
        return value


class Exercise(BaseModel):
    description: str = Field(min_length=1, max_length=800)
    starterCode: str = Field(default="", max_length=600)
    hint: str = Field(min_length=1, max_length=500)
    solution: str = Field(min_length=1, max_length=1200)


class LearningContentPayload(BaseModel):
    language: str = Field(pattern=r"^[a-z][a-z0-9-]{0,39}$")
    library: str = Field(min_length=1, max_length=80)
    topic: str = Field(min_length=1, max_length=120)
    difficulty: Difficulty
    blocks: list[CodeBlock] = Field(min_length=3, max_length=5)
    exercise: Exercise

    model_config = ConfigDict(extra="forbid")

