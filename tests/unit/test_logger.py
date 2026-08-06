"""Unit tests for Loguru logging setup and privacy filter."""

from pathlib import Path

import pytest
from loguru import logger

from src.core.logger import privacy_redaction_filter, setup_logging


@pytest.mark.unit
def test_privacy_redaction_filter() -> None:
    record: dict = {
        "extra": {
            "user_id": "123",
            "text": "Sensitive Clipboard Text",
            "password": "SecretPassword123",
            "token": "bearer-token-abc",
        }
    }

    assert privacy_redaction_filter(record) is True
    assert record["extra"]["user_id"] == "123"
    assert record["extra"]["text"] == "[REDACTED]"
    assert record["extra"]["password"] == "[REDACTED]"
    assert record["extra"]["token"] == "[REDACTED]"


@pytest.mark.unit
def test_setup_logging(tmp_data_dir: Path) -> None:
    setup_logging(tmp_data_dir, debug=True)
    log_file = tmp_data_dir / "logs" / "batmanoverlay.log"

    logger.info("Test log entry")
    logger.debug("Test debug entry")

    assert log_file.exists()
    content = log_file.read_text(encoding="utf-8")
    assert "Test log entry" in content
