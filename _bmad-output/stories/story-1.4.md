# Story 1.4: Configure Structured Logging

## Status: complete

## Epic
Epic 1: Project Foundation & Core Data Layer

## Description
As a **developer**,
I want **structlog configured with wide event pattern**,
So that **operations emit single comprehensive log events**.

## Acceptance Criteria
- [x] Logger outputs JSON-formatted wide events
- [x] Log events include: operation, outcome, duration_ms fields
- [x] Logger importable from `tasmo_guardian/utils/`

## Technical Notes

### Logger Configuration
```python
# tasmo_guardian/utils/logging.py
import structlog
import time
from functools import wraps

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ]
)

logger = structlog.get_logger()

def log_operation(operation_name):
    """Decorator for wide event logging"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                result = await func(*args, **kwargs)
                duration_ms = int((time.perf_counter() - start) * 1000)
                logger.info(operation_name,
                    operation=operation_name,
                    outcome="success",
                    duration_ms=duration_ms
                )
                return result
            except Exception as e:
                duration_ms = int((time.perf_counter() - start) * 1000)
                logger.error(operation_name,
                    operation=operation_name,
                    outcome="error",
                    error=str(e),
                    duration_ms=duration_ms
                )
                raise
        return wrapper
    return decorator
```

### Wide Event Example
```python
logger.info("backup_operation",
    operation="backup_device",
    device_id=1,
    device_ip="192.168.1.10",
    device_type="tasmota",
    outcome="success",
    duration_ms=1247
)
```

## Dependencies
- story-1.1

## FRs Covered
- Architecture requirement: Wide events logging

## Definition of Done
- [x] Code complete - structlog configured
- [x] Wide events emit correctly
- [x] Logger importable from utils
