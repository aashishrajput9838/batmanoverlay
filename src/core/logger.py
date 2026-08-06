"""Loguru logging setup for batmanoverlay."""

import sys
from pathlib import Path
from typing import Any

from loguru import logger

from src.constants import LOG_FILE, LOG_FORMAT, LOG_MAX_SIZE_BYTES, LOG_RETENTION_COUNT


def privacy_redaction_filter(record: Any) -> bool:
    """Filter stripping sensitive fields from structured logging context."""
    sensitive_keys = {
        "text",
        "password",
        "token",
        "cookie",
        "session_id",
        "credential",
    }
    extra = record.get("extra", {})
    for key in list(extra.keys()):
        if key.lower() in sensitive_keys:
            extra[key] = "[REDACTED]"
    return True


def setup_logging(data_dir: Path, debug: bool = False) -> None:
    """Configure Loguru logger sinks."""
    logger.remove()

    log_level = "DEBUG" if debug else "INFO"
    log_dir = data_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file_path = log_dir / LOG_FILE

    logger.add(
        sink=log_file_path,
        level=log_level,
        format=LOG_FORMAT,
        rotation=LOG_MAX_SIZE_BYTES,
        retention=LOG_RETENTION_COUNT,
        compression="gz",
        filter=privacy_redaction_filter,
        enqueue=True,
        encoding="utf-8",
    )

    if debug:
        logger.add(
            sink=sys.stderr,
            level="DEBUG",
            format=LOG_FORMAT,
            filter=privacy_redaction_filter,
        )

    logger.info(f"Logging initialized at level {log_level}")
