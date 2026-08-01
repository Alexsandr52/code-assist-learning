from pydantic import BaseModel, Field
from .content import ContentSource, Difficulty, Exercise, CodeBlock


class PracticeSessionCreate(BaseModel):
    language: str = Field(min_length=1, max_length=40, pattern=r"^[a-z][a-z0-9-]{0,39}$")
    library: str = Field(min_length=1, max_length=40, pattern=r"^[a-z][a-z0-9-]{0,39}$")
    topic: str = Field(min_length=1, max_length=80, pattern=r"^[a-z][a-z0-9-]{0,79}$")
    difficulty: Difficulty
    variant: int | None = Field(default=None, ge=1, le=24)
    anonymousSessionId: str | None = Field(default=None, max_length=80)


class PracticeSessionOut(BaseModel):
    sessionId: str
    source: ContentSource
    language: str
    library: str
    topic: str
    difficulty: Difficulty
    blocks: list[CodeBlock]
    exercise: Exercise


class CompleteSessionIn(BaseModel):
    accuracy: float | None = Field(default=None, ge=0, le=100)
    durationMs: int | None = Field(default=None, ge=0)
    pasteAttempts: int = Field(default=0, ge=0)


class CompleteSessionOut(BaseModel):
    sessionId: str
    status: str
