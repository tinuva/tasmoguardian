# Story 1.3: Database Connection and Session Management

## Status: complete

## Epic
Epic 1: Project Foundation & Core Data Layer

## Description
As a **developer**,
I want **SQLite database connection with proper session management**,
So that **the application can persist and retrieve data reliably**.

## Acceptance Criteria
- [x] SQLite database created at `data/tasmobackupdb.sqlite3` if not exists
- [x] Database sessions properly managed (created/closed)
- [x] `data/backups/` directory created if not exists
- [x] Existing v1 database files readable without modification

## Technical Notes

### Database Module
```python
# tasmo_guardian/models/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from pathlib import Path

DATA_DIR = Path("data")
DB_PATH = DATA_DIR / "tasmobackupdb.sqlite3"
BACKUP_DIR = DATA_DIR / "backups"

def init_db():
    DATA_DIR.mkdir(exist_ok=True)
    BACKUP_DIR.mkdir(exist_ok=True)
    
    engine = create_engine(f"sqlite:///{DB_PATH}")
    Base.metadata.create_all(engine)
    return engine

def get_session():
    engine = init_db()
    Session = sessionmaker(bind=engine)
    return Session()
```

### Context Manager Pattern
```python
from contextlib import contextmanager

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
```

## Dependencies
- story-1.2

## FRs Covered
- FR32

## Definition of Done
- [x] Code complete - database initializes correctly
- [x] Tests written - session management tests
- [x] Tests passing
- [x] V1 database imports without errors
