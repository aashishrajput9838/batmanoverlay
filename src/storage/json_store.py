"""Atomic JSON storage engine."""

import json
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel

from src.storage.exceptions import JsonFileError
from src.storage.file_utils import atomic_write

T = TypeVar("T", bound=BaseModel)


class JsonStore:
    """Provides atomic read and write operations for JSON files and Pydantic models."""

    def read(self, path: Path) -> dict[str, Any]:
        """Read JSON file content as a dictionary.

        Raises:
            JsonFileError: If reading or parsing fails.
        """
        if not path.exists():
            raise JsonFileError(f"JSON file not found: {path}")

        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
                if not isinstance(data, dict):
                    raise JsonFileError(f"Root JSON element is not an object in {path}")
                return data
        except Exception as err:
            raise JsonFileError(f"Failed to read JSON file {path}: {err}") from err

    def write_atomic(self, path: Path, data: dict[str, Any] | BaseModel) -> None:
        """Atomically write dictionary or Pydantic model to a JSON file.

        Raises:
            JsonFileError: If serialization or writing fails.
        """
        try:
            if isinstance(data, BaseModel):
                payload = data.model_dump_json(indent=2)
            else:
                payload = json.dumps(data, indent=2)

            atomic_write(path, payload)
        except Exception as err:
            raise JsonFileError(f"Failed to write JSON atomically to {path}: {err}") from err
