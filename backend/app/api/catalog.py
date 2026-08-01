from fastapi import APIRouter, HTTPException, Query
from app.schemas.content import Difficulty
from app.services.catalog import list_languages, list_libraries, list_topics


router = APIRouter(prefix="/api", tags=["catalog"])


@router.get("/languages")
def get_languages():
    return list_languages()


@router.get("/libraries")
def get_libraries(language: str = Query(min_length=1, max_length=40)):
    libraries = list_libraries(language)
    if not libraries:
        raise HTTPException(status_code=404, detail="language not found or has no active libraries")
    return libraries


@router.get("/topics")
def get_topics(library: str = Query(min_length=1, max_length=40), difficulty: Difficulty | None = None):
    topics = list_topics(library, difficulty)
    if not topics:
        raise HTTPException(status_code=404, detail="library not found or has no active topics")
    return topics

