import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.schemas.practice import (
    CompleteSessionIn,
    CompleteSessionOut,
    PracticeSessionCreate,
    PracticeSessionOut,
)
from app.services.content_service import ContentService


router = APIRouter(prefix="/api/practice-sessions", tags=["practice"])
logger = logging.getLogger("app.api.practice")


def get_content_service(
    settings: Settings = Depends(get_settings),
    db: Session | None = Depends(get_db),
) -> ContentService:
    return ContentService(settings=settings, db=db)


@router.post("", response_model=PracticeSessionOut)
async def create_practice_session(
    payload: PracticeSessionCreate,
    service: ContentService = Depends(get_content_service),
):
    try:
        return await service.create_practice_session(payload)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception(
            "Failed to create practice session: language=%s library=%s topic=%s difficulty=%s",
            payload.language,
            payload.library,
            payload.topic,
            payload.difficulty,
        )
        raise HTTPException(status_code=503, detail="practice session generation is unavailable") from exc


@router.get("/{session_id}", response_model=PracticeSessionOut)
def get_practice_session(session_id: str, service: ContentService = Depends(get_content_service)):
    try:
        return service.get_practice_session(session_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{session_id}/complete", response_model=CompleteSessionOut)
def complete_practice_session(
    session_id: str,
    payload: CompleteSessionIn,
    service: ContentService = Depends(get_content_service),
):
    try:
        return service.complete_practice_session(session_id, payload)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
