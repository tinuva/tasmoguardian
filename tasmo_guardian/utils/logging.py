"""Structured logging with wide event pattern."""

import time
from functools import wraps

import structlog

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ]
)

logger = structlog.get_logger()


def log_operation(operation_name: str):
    """Decorator for wide event logging."""

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                result = await func(*args, **kwargs)
                duration_ms = int((time.perf_counter() - start) * 1000)
                logger.info(
                    operation_name,
                    operation=operation_name,
                    outcome="success",
                    duration_ms=duration_ms,
                )
                return result
            except Exception as e:
                duration_ms = int((time.perf_counter() - start) * 1000)
                logger.error(
                    operation_name,
                    operation=operation_name,
                    outcome="error",
                    error=str(e),
                    duration_ms=duration_ms,
                )
                raise

        return wrapper

    return decorator
