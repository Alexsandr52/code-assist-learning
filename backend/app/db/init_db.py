from app.db.session import engine
from app.models.base import Base

# Import models so SQLAlchemy registers them before create_all.
from app.models.cache import ContentCache  # noqa: F401
from app.models.catalog import Language, Library  # noqa: F401
from app.models.content import LearningContent, Topic  # noqa: F401
from app.models.session import PracticeSession  # noqa: F401


def init_db() -> None:
    if engine is None:
        return
    Base.metadata.create_all(bind=engine)

