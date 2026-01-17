"""Tests for SQLAlchemy models."""

from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from tasmo_guardian.models import Backup, Base, Device, DeviceType, Setting


def test_device_model_columns():
    """AC: Device model has exact v1 column names."""
    cols = {c.name for c in Device.__table__.columns}
    expected = {"id", "name", "ip", "mac", "type", "version", "lastbackup", "noofbackups", "password"}
    assert cols == expected


def test_device_type_values():
    """AC: type column uses integer (0=Tasmota, 1=WLED)."""
    assert DeviceType.TASMOTA == 0
    assert DeviceType.WLED == 1


def test_device_instantiation():
    """DoD: model instantiation test."""
    device = Device(
        name="Test Device",
        ip="192.168.1.10",
        mac="AABBCCDDEEFF",
        type=DeviceType.TASMOTA,
        version="13.1.0",
        lastbackup=datetime.now(),
        noofbackups=5,
        password="secret",
    )
    assert device.name == "Test Device"
    assert device.type == 0


def test_backup_model_columns():
    """Backup model matches v1 schema."""
    cols = {c.name for c in Backup.__table__.columns}
    expected = {"id", "deviceid", "name", "version", "date", "filename", "data"}
    assert cols == expected


def test_setting_model_columns():
    """Setting model matches v1 schema."""
    cols = {c.name for c in Setting.__table__.columns}
    expected = {"name", "value"}
    assert cols == expected


def test_v1_database_readable():
    """DoD: V1 database readable with these models."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        device = Device(
            name="Kitchen Plug",
            ip="192.168.1.50",
            mac="AABBCCDDEEFF",
            type=DeviceType.TASMOTA,
            version="13.1.0",
        )
        session.add(device)
        session.commit()

        loaded = session.query(Device).filter_by(ip="192.168.1.50").first()
        assert loaded.name == "Kitchen Plug"
        assert loaded.mac == "AABBCCDDEEFF"
