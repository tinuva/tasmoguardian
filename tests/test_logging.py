"""Tests for structured logging."""

import asyncio
import json

from tasmo_guardian.utils import log_operation, logger


def test_logger_importable():
    """AC: Logger importable from tasmo_guardian/utils/."""
    from tasmo_guardian.utils import logger

    assert logger is not None


def test_wide_event_fields(capsys):
    """AC: Log events include operation, outcome, duration_ms."""
    logger.info(
        "test_operation",
        operation="test_op",
        outcome="success",
        duration_ms=100,
    )
    captured = capsys.readouterr()
    log_data = json.loads(captured.out)
    assert log_data["operation"] == "test_op"
    assert log_data["outcome"] == "success"
    assert log_data["duration_ms"] == 100
    assert "timestamp" in log_data


def test_log_operation_decorator(capsys):
    """AC: Decorator emits wide events."""

    @log_operation("test_decorated")
    async def sample_func():
        return "done"

    result = asyncio.run(sample_func())
    assert result == "done"

    captured = capsys.readouterr()
    log_data = json.loads(captured.out)
    assert log_data["operation"] == "test_decorated"
    assert log_data["outcome"] == "success"
    assert "duration_ms" in log_data
