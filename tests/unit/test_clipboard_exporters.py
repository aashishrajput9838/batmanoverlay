"""Unit tests for ClipboardExporter contracts."""

import pytest

from src.clipboard.exporters import ClipboardExporter
from src.models.clipboard import ClipboardItem


@pytest.mark.unit
def test_json_export_and_import() -> None:
    items = [
        ClipboardItem(content="Line 1\nLine 2"),
        ClipboardItem(content="Second entry", is_pinned=True),
    ]

    json_data = ClipboardExporter.export_json(items)
    assert "Line 1" in json_data

    imported = ClipboardExporter.import_json(json_data)
    assert len(imported) == 2
    assert imported[0].content == "Line 1\nLine 2"
    assert imported[1].is_pinned is True


@pytest.mark.unit
def test_csv_and_txt_export() -> None:
    items = [
        ClipboardItem(content="Alpha"),
        ClipboardItem(content="Beta"),
    ]

    csv_data = ClipboardExporter.export_csv(items)
    assert "Alpha" in csv_data
    assert "content_type" in csv_data

    txt_data = ClipboardExporter.export_txt(items)
    assert "Alpha\n\n---\n\nBeta" in txt_data
