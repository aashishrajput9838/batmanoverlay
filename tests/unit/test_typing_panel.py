"""Unit tests for production TypingPanel UI component."""

import time

import pytest
from PySide6.QtCore import QCoreApplication

from src.core.events import AppSignals
from src.platform.mock_target import MockKeyInputSender, MockTargetAcquirer
from src.platform.models import TargetInfo
from src.typing.config import TypingConfig
from src.typing.engine import HumanTypingEngine
from src.ui.dialogs import TargetPreviewDialog
from src.ui.typing_panel import TypingPanel


@pytest.mark.unit
def test_typing_panel_initialization() -> None:
    engine = HumanTypingEngine(
        target_acquirer=MockTargetAcquirer(),
        input_sender=MockKeyInputSender(),
    )
    signals = AppSignals()
    panel = TypingPanel(engine, signals)

    assert panel._lbl_status.text() == "READY"
    assert panel._btn_start.isEnabled() is True
    assert panel._btn_pause.isEnabled() is False
    assert panel._btn_stop.isEnabled() is False

    # Test 2000 WPM range
    assert panel._spin_wpm.maximum() == 2000
    assert panel._slider_wpm.maximum() == 2000
    panel._spin_wpm.setValue(2000)
    assert panel._spin_wpm.value() == 2000
    assert panel._get_current_config().speed_wpm == 2000.0


@pytest.mark.unit
def test_typing_panel_text_stats_update() -> None:
    engine = HumanTypingEngine(
        target_acquirer=MockTargetAcquirer(),
        input_sender=MockKeyInputSender(),
    )
    signals = AppSignals()
    panel = TypingPanel(engine, signals)

    panel._txt_input.setPlainText("Hello World\nLine 2")
    QCoreApplication.processEvents()

    stats_text = panel._lbl_text_stats.text()
    assert "18 characters" in stats_text
    assert "4 words" in stats_text
    assert "2 lines" in stats_text


@pytest.mark.unit
def test_typing_panel_target_display_update() -> None:
    engine = HumanTypingEngine(
        target_acquirer=MockTargetAcquirer(),
        input_sender=MockKeyInputSender(),
    )
    signals = AppSignals()
    panel = TypingPanel(engine, signals)

    mock_target = TargetInfo(
        window_title="Notepad - Test.txt",
        process_name="notepad.exe",
        control_type="Edit",
        hwnd_window=1001,
        hwnd_control=2002,
    )
    panel._update_target_display(mock_target)
    QCoreApplication.processEvents()

    assert panel._lbl_target_win.text() == "<b>Notepad - Test.txt</b>"
    assert panel._lbl_target_proc.text() == "<code>notepad.exe</code>"


@pytest.mark.unit
def test_typing_panel_start_and_complete_flow() -> None:
    engine = HumanTypingEngine(
        target_acquirer=MockTargetAcquirer(),
        input_sender=MockKeyInputSender(),
    )
    signals = AppSignals()
    panel = TypingPanel(engine, signals)

    config = TypingConfig(
        start_delay_seconds=0.0,
        show_preview_dialog=False,
        speed_wpm=300.0,
        min_delay_ms=5,
        max_delay_ms=10,
    )
    engine.set_default_config(config)

    panel._combo_delay.setCurrentIndex(0)
    panel._chk_preview.setChecked(False)
    panel._chk_humanized_rhythm.setChecked(False)
    panel._spin_wpm.setValue(300)

    panel._txt_input.setPlainText("Fast Text")
    panel._on_start_typing()

    worker = engine._scheduler._active_worker
    if worker:
        for _ in range(200):
            if not worker.isRunning():
                break
            QCoreApplication.processEvents()
            time.sleep(0.02)

    QCoreApplication.processEvents()

    # Completed job resets UI state back to READY for next job
    assert panel._lbl_status.text() == "READY"
    assert panel._btn_start.isEnabled() is True


@pytest.mark.unit
def test_target_preview_dialog_modal() -> None:
    target = TargetInfo(
        window_title="Notepad - ModalTest.txt",
        process_name="notepad.exe",
        control_type="Edit",
        hwnd_window=100,
        hwnd_control=200,
    )
    dlg = TargetPreviewDialog(target, 500, 15.0)
    assert dlg.windowTitle() == "Typing Target Preview"
    assert dlg.dont_show_again() is False
