"""Tests for database connection and session management."""

import tempfile
from pathlib import Path
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from tasmo_guardian.models import BACKUP_DIR, DATA_DIR, Base, Device, DeviceType, db_session
from tasmo_guardian.models.database import get_engine, get_session


def test_directories_created():
    """AC: data/ and data/backups/ directories created."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_data = Path(tmpdir) / "data"
        test_backup = test_data / "backups"
        test_db = test_data / "test.sqlite3"

        with patch("tasmo_guardian.models.database.DATA_DIR", test_data), patch(
            "tasmo_guardian.models.database.BACKUP_DIR", test_backup
        ), patch("tasmo_guardian.models.database.DB_PATH", test_db), patch(
            "tasmo_guardian.models.database._engine", None
        ):
            engine = get_engine()
            assert test_data.exists()
            assert test_backup.exists()
            assert test_db.exists()


def test_session_returns_session():
    """AC: Database sessions properly managed."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_data = Path(tmpdir) / "data"
        test_backup = test_data / "backups"
        test_db = test_data / "test.sqlite3"

        with patch("tasmo_guardian.models.database.DATA_DIR", test_data), patch(
            "tasmo_guardian.models.database.BACKUP_DIR", test_backup
        ), patch("tasmo_guardian.models.database.DB_PATH", test_db), patch(
            "tasmo_guardian.models.database._engine", None
        ):
            session = get_session()
            assert isinstance(session, Session)
            session.close()


def test_db_session_context_manager():
    """AC: Context manager commits and closes."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_data = Path(tmpdir) / "data"
        test_backup = test_data / "backups"
        test_db = test_data / "test.sqlite3"

        with patch("tasmo_guardian.models.database.DATA_DIR", test_data), patch(
            "tasmo_guardian.models.database.BACKUP_DIR", test_backup
        ), patch("tasmo_guardian.models.database.DB_PATH", test_db), patch(
            "tasmo_guardian.models.database._engine", None
        ):
            with db_session() as session:
                device = Device(
                    name="Test",
                    ip="192.168.1.1",
                    mac="AABBCC",
                    type=DeviceType.TASMOTA,
                    version="13.0",
                )
                session.add(device)

            # Verify persisted
            with db_session() as session:
                loaded = session.query(Device).first()
                assert loaded.name == "Test"


def test_v1_database_import():
    """AC: Existing v1 database files readable."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "v1test.sqlite3"
        engine = create_engine(f"sqlite:///{db_path}")
        Base.metadata.create_all(engine)

        # Insert v1-style data
        with Session(engine) as session:
            device = Device(
                name="V1 Device",
                ip="10.0.0.1",
                mac="112233445566",
                type=0,
                version="12.0.0",
                noofbackups=3,
            )
            session.add(device)
            session.commit()

        # Read with new code
        with Session(engine) as session:
            loaded = session.query(Device).first()
            assert loaded.name == "V1 Device"
            assert loaded.noofbackups == 3
