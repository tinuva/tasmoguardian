# Story 1.2: Create SQLAlchemy Models with V1 Schema

## Status: complete

## Epic
Epic 1: Project Foundation & Core Data Layer

## Description
As a **developer**,
I want **SQLAlchemy models that match the v1 database schema exactly**,
So that **existing v1 databases can be imported without migration**.

## Acceptance Criteria
- [x] Device model has columns: id, name, ip, mac, type, version, lastbackup, noofbackups, password
- [x] type column uses integer (0=Tasmota, 1=WLED)
- [x] Column names match v1 exactly (lastbackup, noofbackups - no underscores)
- [x] Models are in `tasmo_guardian/models/` directory
- [x] Settings model matches v1 schema

## Technical Notes

### Device Model (CRITICAL: exact column names)
```python
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class Device(Base):
    __tablename__ = "devices"
    
    id = Column(Integer, primary_key=True)
    name = Column(String)
    ip = Column(String)
    mac = Column(String)
    type = Column(Integer)  # 0=Tasmota, 1=WLED
    version = Column(String)
    lastbackup = Column(DateTime)  # NOT last_backup
    noofbackups = Column(Integer)  # NOT num_backups
    password = Column(String)
```

### Device Type Enum
```python
class DeviceType:
    TASMOTA = 0
    WLED = 1
```

## Dependencies
- story-1.1

## FRs Covered
- FR32

## Definition of Done
- [x] Code complete - models match v1 schema exactly
- [x] Tests written - model instantiation tests
- [x] Tests passing
- [x] V1 database readable with these models
