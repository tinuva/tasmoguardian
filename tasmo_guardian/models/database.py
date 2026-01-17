"""Database connection and session management."""

from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from tasmo_guardian.models.device import Base

DATA_DIR = Path("data")
DB_PATH = DATA_DIR / "tasmobackupdb.sqlite3"
BACKUP_DIR = DATA_DIR / "backups"

_engine = None


def get_engine():
    global _engine
    if _engine is None:
        DATA_DIR.mkdir(exist_ok=True)
        BACKUP_DIR.mkdir(exist_ok=True)
        _engine = create_engine(f"sqlite:///{DB_PATH}")
        Base.metadata.create_all(_engine)
    return _engine


def get_session() -> Session:
    return sessionmaker(bind=get_engine())()


@contextmanager
def db_session():
    session = get_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
