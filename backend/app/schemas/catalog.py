from pydantic import BaseModel
from .content import Difficulty


class LanguageOut(BaseModel):
    id: str
    name: str
    slug: str


class LibraryOut(BaseModel):
    id: str
    language: str
    name: str
    slug: str
    description: str


class TopicOut(BaseModel):
    id: str
    library: str
    name: str
    slug: str
    difficulty: Difficulty

