"""SQLAlchemy models matching v1 schema exactly."""

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class DeviceType:
    TASMOTA = 0
    WLED = 1


class Device(Base):
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(128), nullable=False)
    ip = Column(String(64), nullable=False)
    mac = Column(String(32), nullable=False)
    type = Column(Integer, nullable=False, default=0)
    version = Column(String(128), nullable=False)
    lastbackup = Column(DateTime)
    noofbackups = Column(Integer)
    password = Column(String(128))

    backups = relationship("Backup", back_populates="device", cascade="all, delete-orphan")


class Backup(Base):
    __tablename__ = "backups"

    id = Column(Integer, primary_key=True, autoincrement=True)
    deviceid = Column(Integer, ForeignKey("devices.id"), nullable=False)
    name = Column(String(128), nullable=False)
    version = Column(String(128), nullable=False)
    date = Column(DateTime)
    filename = Column(String(1080))
    data = Column(Text)

    device = relationship("Device", back_populates="backups")

    __table_args__ = (Index("backupsdeviceid", "deviceid", "date"),)


class Setting(Base):
    __tablename__ = "settings"

    name = Column(String(128), primary_key=True, nullable=False)
    value = Column(String(255), nullable=False)
