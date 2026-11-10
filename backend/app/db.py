"""Database engine and session factory.

Tests (and run_scenarios.py) call init_engine(url) to point everything, including the
background workflow, at a throwaway database.
"""

from collections.abc import Iterator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings


class Base(DeclarativeBase):
    pass


SessionLocal: sessionmaker[Session] = sessionmaker(autoflush=False, expire_on_commit=False)
engine: Engine | None = None


def init_engine(url: str | None = None) -> Engine:
    """(Re)create the engine, bind SessionLocal and create all tables."""
    global engine
    url = url or settings.DATABASE_URL
    kwargs: dict = {}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
        if url in ("sqlite://", "sqlite:///:memory:"):
            kwargs["poolclass"] = StaticPool
    if engine is not None:
        engine.dispose()
    engine = create_engine(url, **kwargs)
    SessionLocal.configure(bind=engine)
    from app import models  # noqa: F401  (register tables)

    Base.metadata.create_all(engine)
    return engine


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
