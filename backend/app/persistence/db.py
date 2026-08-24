"""SQLite Database Connection and Session Management (TRD Section 10, ADR-007)."""

from contextlib import contextmanager
import logging
from pathlib import Path
from typing import Generator, Optional
from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker, Session

from backend.app.core.config import get_project_root, settings

logger = logging.getLogger("sovereign_workbench.persistence.db")

Base = declarative_base()

_engine = None
_SessionFactory = None


def get_db_path(custom_path: Optional[Path] = None) -> Path:
    if custom_path is not None:
        return custom_path
    data_dir = get_project_root() / settings.paths.data_dir
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "app.db"


def get_engine(db_path: Optional[Path] = None):
    global _engine
    if _engine is None or db_path is not None:
        resolved_path = get_db_path(db_path)
        db_url = f"sqlite:///{resolved_path}"
        eng = create_engine(
            db_url,
            connect_args={"check_same_thread": False},
            echo=False,
        )

        @event.listens_for(eng, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL;")
            cursor.execute("PRAGMA synchronous=NORMAL;")
            cursor.execute("PRAGMA foreign_keys=ON;")
            cursor.close()

        if db_path is None:
            _engine = eng
            Base.metadata.create_all(bind=_engine)
            return _engine
        else:
            Base.metadata.create_all(bind=eng)
            return eng

    return _engine


def get_session_factory(db_path: Optional[Path] = None):
    global _SessionFactory
    if _SessionFactory is None or db_path is not None:
        engine = get_engine(db_path)
        factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        if db_path is None:
            _SessionFactory = factory
            return _SessionFactory
        return factory
    return _SessionFactory


def init_db(db_path: Optional[Path] = None) -> None:
    """Create tables if they do not exist."""
    engine = get_engine(db_path)
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables initialized with WAL mode enabled")


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency / generator providing a DB session."""
    factory = get_session_factory()
    session: Session = factory()
    try:
        yield session
    finally:
        session.close()


@contextmanager
def get_db_context(db_path: Optional[Path] = None) -> Generator[Session, None, None]:
    """Context manager for standalone script and background task database access."""
    factory = get_session_factory(db_path)
    session: Session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
