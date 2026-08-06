"""Unit tests for JsonStore and atomic writing."""

from pathlib import Path

import pytest

from src.core.exceptions import JsonFileError
from src.models.settings import AppSettings
from src.storage.json_store import JsonStore


@pytest.mark.unit
def test_json_store_write_and_read_dict(tmp_path: Path) -> None:
    store = JsonStore()
    file_path = tmp_path / "test.json"
    data = {"key": "value", "number": 42}

    store.write_atomic(file_path, data)
    assert file_path.exists()

    result = store.read(file_path)
    assert result == data


@pytest.mark.unit
def test_json_store_write_and_read_model(tmp_path: Path) -> None:
    store = JsonStore()
    file_path = tmp_path / "settings.json"
    settings = AppSettings()

    store.write_atomic(file_path, settings)
    assert file_path.exists()

    result = store.read(file_path)
    assert result["version"] == 1
    assert result["general"]["language"] == "en"


@pytest.mark.unit
def test_json_store_read_nonexistent_file(tmp_path: Path) -> None:
    store = JsonStore()
    file_path = tmp_path / "missing.json"

    with pytest.raises(JsonFileError):
        store.read(file_path)


@pytest.mark.unit
def test_json_store_read_invalid_json(tmp_path: Path) -> None:
    store = JsonStore()
    file_path = tmp_path / "corrupt.json"
    file_path.write_text("NOT JSON CONTENT", encoding="utf-8")

    with pytest.raises(JsonFileError):
        store.read(file_path)
