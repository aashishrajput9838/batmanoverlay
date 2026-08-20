import ctypes
import sys
import time
from typing import Any

import pytest
from PySide6.QtCore import QCoreApplication, Qt

from src.platform import get_platform_input_sender, get_platform_target_acquirer
from src.platform.mock_target import MockKeyInputSender, MockTargetAcquirer
from src.platform.windows_target import INPUT, WindowsKeyInputSender, WindowsTargetAcquirer
from src.typing.config import TypingConfig
from src.typing.engine import HumanTypingEngine
from src.typing.events import TypingAction, TypingSignals
from src.typing.queue import JobStatus, TypingJob, TypingQueue
from src.typing.simulator import HumanTypingSimulator, parse_grapheme_clusters
from src.typing.target import TargetInfo
from src.typing.worker import TypingWorker


# --------------------------------------------------------------------
# 1. TypingConfig Tests
# --------------------------------------------------------------------
@pytest.mark.unit
def test_typing_config_defaults_and_estimation() -> None:
    config = TypingConfig()
    assert config.speed_wpm == 60.0
    assert config.start_delay_seconds == 10.0
    assert config.show_preview_dialog is False
    assert config.emergency_abort_key == "Escape"

    # Duration estimation for 300 characters (60 words at 60 WPM = 60s base)
    est_60wpm = config.calculate_estimated_duration_seconds(300)
    assert est_60wpm > 55.0

    # Duration estimation for text exceeding paste threshold
    est_paste = config.calculate_estimated_duration_seconds(600)
    assert est_paste == 0.5


@pytest.mark.unit
def test_typing_config_high_speed_wpm_limit() -> None:
    """Verify TypingConfig accepts speeds up to 2000 WPM without internal clamping or errors."""
    config_2000 = TypingConfig(speed_wpm=2000.0, humanized_rhythm_enabled=False)
    assert config_2000.speed_wpm == 2000.0

    # Test duration estimation at 2000 WPM
    est = config_2000.calculate_estimated_duration_seconds(400)
    assert est < 30.0

    # Test legacy backward compatibility WPM values
    for legacy_wpm in [5.0, 60.0, 120.0, 250.0, 300.0]:
        cfg = TypingConfig(speed_wpm=legacy_wpm)
        assert cfg.speed_wpm == legacy_wpm

    # Test out of bounds validation (> 2000 WPM)
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        TypingConfig(speed_wpm=2001.0)


# --------------------------------------------------------------------
# 2. Simulator & Grapheme Tests
# --------------------------------------------------------------------
@pytest.mark.unit
def test_grapheme_cluster_parsing() -> None:
    text = "Hello 🚀 👨‍👩‍👧‍👦 World\nLine2"
    clusters = parse_grapheme_clusters(text)
    assert "H" in clusters
    assert "🚀" in clusters
    assert "👨‍👩‍👧‍👦" in clusters
    assert "\n" in clusters


@pytest.mark.unit
def test_simulator_plan_generation_and_typos() -> None:
    simulator = HumanTypingSimulator()
    config = TypingConfig(
        speed_wpm=120.0,
        mistake_probability=0.5,  # High typo rate for testing
        random_seed=42,
    )

    plan = simulator.generate_plan("Python Code", config)
    assert len(plan) > 0

    actions = [s.action_type for s in plan]
    assert TypingAction.TYPE_CHAR in actions
    # Should contain backspace due to mistake probability
    assert TypingAction.BACKSPACE in actions or TypingAction.PAUSE in actions


@pytest.mark.unit
def test_simulator_empty_text() -> None:
    simulator = HumanTypingSimulator()
    config = TypingConfig()
    plan = simulator.generate_plan("", config)
    assert len(plan) == 0


@pytest.mark.unit
def test_simulator_paste_threshold_fallback() -> None:
    simulator = HumanTypingSimulator()
    config = TypingConfig(paste_threshold_chars=50)

    large_text = "A" * 100
    plan = simulator.generate_plan(large_text, config)

    assert len(plan) == 1
    assert plan[0].action_type == TypingAction.PASTE_CHUNK
    assert plan[0].char == large_text

    # Test disabled enable_paste_threshold (forces character-by-character typing)
    config_disabled = TypingConfig(
        paste_threshold_chars=50,
        enable_paste_threshold=False,
        mistake_probability=0.0,
        humanized_rhythm_enabled=False,
    )
    plan_disabled = simulator.generate_plan(large_text, config_disabled)
    assert len(plan_disabled) == 100
    assert plan_disabled[0].action_type == TypingAction.TYPE_CHAR


# --------------------------------------------------------------------
# 3. Target Acquisition & Safety Validation Tests
# --------------------------------------------------------------------
@pytest.mark.unit
def test_target_validation_rules() -> None:
    win_acquirer = WindowsTargetAcquirer()

    # Valid editor control
    valid_target = TargetInfo(
        window_title="VS Code",
        process_name="code.exe",
        control_type="Scintilla",
        hwnd_window=1,
        hwnd_control=2,
    )
    res_valid = win_acquirer.validate_target(valid_target)
    assert res_valid.is_valid is True
    assert res_valid.target_info is not None
    assert valid_target.to_dict()["window_title"] == "VS Code"

    # None target failure
    res_none = win_acquirer.validate_target(None)
    assert res_none.is_valid is False

    # Zero HWND window failure
    invalid_hwnd = TargetInfo(
        window_title="Test",
        process_name="test.exe",
        control_type="Edit",
        hwnd_window=0,
        hwnd_control=0,
    )
    res_invalid_hwnd = win_acquirer.validate_target(invalid_hwnd)
    assert res_invalid_hwnd.is_valid is False

    # Desktop background rejection
    desktop_target = TargetInfo(
        window_title="Program Manager",
        process_name="explorer.exe",
        control_type="Progman",
        hwnd_window=1,
        hwnd_control=2,
    )
    res_desktop = win_acquirer.validate_target(desktop_target)
    assert res_desktop.is_valid is False
    assert "Desktop" in res_desktop.reason

    # Taskbar rejection
    taskbar_target = TargetInfo(
        window_title="",
        process_name="explorer.exe",
        control_type="Shell_TrayWnd",
        hwnd_window=1,
        hwnd_control=2,
    )
    res_taskbar = win_acquirer.validate_target(taskbar_target)
    assert res_taskbar.is_valid is False


@pytest.mark.unit
def test_platform_factory_getters() -> None:
    acquirer = get_platform_target_acquirer()
    sender = get_platform_input_sender()
    assert acquirer is not None
    assert sender is not None


# --------------------------------------------------------------------
# 4. Queue Thread Safety & Priority Tests
# --------------------------------------------------------------------
@pytest.mark.unit
def test_typing_queue_operations() -> None:
    t_queue = TypingQueue()
    cfg = TypingConfig()

    job1 = TypingJob(text="Job 1", config=cfg, priority=10)
    job2 = TypingJob(text="Job 2 High Priority", config=cfg, priority=1)

    t_queue.push(job1)
    t_queue.push(job2)

    assert t_queue.size() == 2
    assert t_queue.peek() is not None

    # Higher priority (priority=1) should pop first
    popped = t_queue.pop()
    assert popped is not None
    assert popped.job_id == job2.job_id

    # Cancel job 1
    assert t_queue.cancel_job(job1.job_id, "Test cancel") is True
    assert job1.status == JobStatus.CANCELLED

    # Cancel already cancelled job returns False
    assert t_queue.cancel_job(job1.job_id) is False

    # Retrieve job 1
    retrieved = t_queue.get_job(job1.job_id)
    assert retrieved is not None
    assert retrieved.job_id == job1.job_id

    # Peek job (should return None as job2 popped and job1 cancelled)
    assert t_queue.peek() is None

    # Push job and clear queue
    job3 = TypingJob(text="Job 3", config=cfg)
    t_queue.push(job3)
    assert t_queue.clear("Test clear") == 1


# --------------------------------------------------------------------
# 5. Worker & Pipeline End-to-End Tests
# --------------------------------------------------------------------
@pytest.mark.unit
def test_typing_worker_execution_pipeline() -> None:
    signals = TypingSignals()
    events_captured: list[str] = []

    signals.countdown_started.connect(
        lambda _j, _d: events_captured.append("countdown_started"),
        Qt.ConnectionType.DirectConnection,
    )
    signals.target_acquired.connect(
        lambda _j, _t, _c, _e: events_captured.append("target_acquired"),
        Qt.ConnectionType.DirectConnection,
    )
    signals.typing_started.connect(
        lambda _j, _txt: events_captured.append("typing_started"),
        Qt.ConnectionType.DirectConnection,
    )
    signals.completed.connect(
        lambda _j, _dur: events_captured.append("completed"),
        Qt.ConnectionType.DirectConnection,
    )

    config = TypingConfig(
        start_delay_seconds=0.1,  # Fast countdown for test
        show_preview_dialog=False,  # Skip preview wait
        speed_wpm=300.0,
        initial_delay_ms=0,
        min_delay_ms=1,
        max_delay_ms=5,
    )

    job = TypingJob(text="Fast Test", config=config)
    acquirer = MockTargetAcquirer()
    sender = MockKeyInputSender()

    worker = TypingWorker(
        job=job,
        signals=signals,
        target_acquirer=acquirer,
        input_sender=sender,
    )

    worker.start()
    worker.wait(5000)
    QCoreApplication.processEvents()

    assert "countdown_started" in events_captured
    assert "target_acquired" in events_captured
    assert "typing_started" in events_captured
    assert "completed" in events_captured
    assert len(sender.sent_chars) > 0


@pytest.mark.unit
def test_typing_worker_preview_confirmation_flow() -> None:
    signals = TypingSignals()
    preview_events: list[str] = []
    signals.preview_requested.connect(
        lambda _j, _t, _c, _e: preview_events.append("preview_requested"),
        Qt.ConnectionType.DirectConnection,
    )

    config = TypingConfig(
        start_delay_seconds=0.05,
        show_preview_dialog=True,  # Enable preview wait
        speed_wpm=300.0,
        humanized_rhythm_enabled=False,
    )

    job = TypingJob(text="Preview Flow Text", config=config)
    worker = TypingWorker(
        job=job,
        signals=signals,
        target_acquirer=MockTargetAcquirer(),
        input_sender=MockKeyInputSender(),
    )

    worker.start()
    for _ in range(25):
        QCoreApplication.processEvents()
        if preview_events:
            break
        time.sleep(0.02)

    assert "preview_requested" in preview_events
    assert worker.job.status == JobStatus.PREVIEW_WAIT

    # Confirm preview
    worker.confirm_preview()
    for _ in range(200):
        if not worker.isRunning():
            break
        time.sleep(0.05)
        QCoreApplication.processEvents()

    assert worker.job.status == JobStatus.COMPLETED


@pytest.mark.unit
def test_typing_worker_target_validation_failure() -> None:
    signals = TypingSignals()
    failed_reasons: list[str] = []
    signals.target_validation_failed.connect(
        lambda _j, r: failed_reasons.append(r),
        Qt.ConnectionType.DirectConnection,
    )

    config = TypingConfig(start_delay_seconds=0, show_preview_dialog=False)
    job = TypingJob(text="Fail Test", config=config)

    # Mock acquirer returning invalid Desktop target
    acquirer = MockTargetAcquirer(is_valid=False, failure_reason="No editable field focused.")
    sender = MockKeyInputSender()

    worker = TypingWorker(
        job=job,
        signals=signals,
        target_acquirer=acquirer,
        input_sender=sender,
    )

    worker.start()
    worker.wait(3000)
    QCoreApplication.processEvents()

    assert len(failed_reasons) == 1
    assert "No editable field focused" in failed_reasons[0]
    assert len(sender.sent_chars) == 0  # Typing did NOT start


@pytest.mark.unit
def test_typing_worker_cancel_during_countdown() -> None:
    signals = TypingSignals()
    cancelled_events: list[str] = []
    signals.cancelled.connect(
        lambda _j, r: cancelled_events.append(r),
        Qt.ConnectionType.DirectConnection,
    )

    config = TypingConfig(start_delay_seconds=5.0)
    job = TypingJob(text="Cancel Countdown", config=config)

    worker = TypingWorker(
        job=job,
        signals=signals,
        target_acquirer=MockTargetAcquirer(),
        input_sender=MockKeyInputSender(),
    )

    worker.start()
    time.sleep(0.1)
    QCoreApplication.processEvents()

    # Cancel during countdown
    worker.cancel("User cancelled countdown")
    worker.wait(3000)
    QCoreApplication.processEvents()

    assert len(cancelled_events) == 1
    assert worker.is_cancelled() is True


@pytest.mark.unit
def test_typing_worker_paste_chunk_and_backspace_execution() -> None:
    signals = TypingSignals()
    sender = MockKeyInputSender()
    config = TypingConfig(
        start_delay_seconds=0.01,
        show_preview_dialog=False,
        paste_threshold_chars=10,  # Force paste chunk
    )

    job = TypingJob(text="Long text that will trigger paste chunk mode", config=config)
    worker = TypingWorker(
        job=job,
        signals=signals,
        target_acquirer=MockTargetAcquirer(),
        input_sender=sender,
    )

    worker.start()
    worker.wait(3000)
    QCoreApplication.processEvents()

    assert len(sender.sent_pastes) == 1
    assert sender.sent_pastes[0] == "Long text that will trigger paste chunk mode"

    # Test backspace input sender directly
    sender.send_backspace(MockTargetAcquirer().mock_target)
    assert sender.sent_backspaces == 1


# --------------------------------------------------------------------
# 6. Facade Engine & Emergency Abort Tests
# --------------------------------------------------------------------
@pytest.mark.unit
def test_human_typing_engine_facade_and_emergency_abort() -> None:
    engine = HumanTypingEngine(
        target_acquirer=MockTargetAcquirer(),
        input_sender=MockKeyInputSender(),
    )

    config = TypingConfig(
        start_delay_seconds=10.0,  # 10s countdown
        show_preview_dialog=False,
    )

    completed_jobs: list[str] = []
    cancelled_jobs: list[str] = []

    engine.signals.completed.connect(
        lambda j, _d: completed_jobs.append(j),
        Qt.ConnectionType.DirectConnection,
    )
    engine.signals.cancelled.connect(
        lambda j, _r: cancelled_jobs.append(j),
        Qt.ConnectionType.DirectConnection,
    )

    job_id = engine.type_text("Long countdown job", config)
    assert job_id is not None

    time.sleep(0.05)
    QCoreApplication.processEvents()

    # Trigger Emergency Abort (<50ms response)
    start_abort = time.perf_counter()
    assert engine.emergency_abort() is True
    abort_duration_ms = (time.perf_counter() - start_abort) * 1000.0

    if engine._scheduler._active_worker:
        engine._scheduler._active_worker.wait(3000)
    QCoreApplication.processEvents()

    # Response time must be under 50ms
    assert abort_duration_ms < 50.0
    assert len(cancelled_jobs) == 1
    assert len(completed_jobs) == 0


@pytest.mark.unit
def test_engine_pause_resume_cancel() -> None:
    engine = HumanTypingEngine(
        target_acquirer=MockTargetAcquirer(),
        input_sender=MockKeyInputSender(),
    )

    config = TypingConfig(
        start_delay_seconds=0.05,
        show_preview_dialog=False,
        speed_wpm=30.0,  # Slower typing to test pause/resume
        min_delay_ms=50,
        max_delay_ms=100,
    )

    paused_jobs: list[str] = []
    resumed_jobs: list[str] = []

    engine.signals.paused.connect(lambda j: paused_jobs.append(j))
    engine.signals.resumed.connect(lambda j: resumed_jobs.append(j))

    _job_id = engine.type_text("Testing pause and resume functionality", config)
    time.sleep(0.1)
    QCoreApplication.processEvents()

    # Pause engine
    assert engine.pause() is True
    QCoreApplication.processEvents()
    assert len(paused_jobs) == 1

    # Check worker pause state
    if engine._scheduler._active_worker:
        assert engine._scheduler._active_worker.is_paused() is True

    # Resume engine
    assert engine.resume() is True
    QCoreApplication.processEvents()
    assert len(resumed_jobs) == 1

    # Cancel engine
    assert engine.cancel("User cancel test") is True
    if engine._scheduler._active_worker:
        engine._scheduler._active_worker.wait(3000)
    QCoreApplication.processEvents()


@pytest.mark.unit
def test_engine_preview_confirm_and_cancel() -> None:
    engine = HumanTypingEngine(
        target_acquirer=MockTargetAcquirer(),
        input_sender=MockKeyInputSender(),
    )

    config = TypingConfig(
        start_delay_seconds=0.01,
        show_preview_dialog=True,
        speed_wpm=300.0,
    )

    # Test confirm preview facade call
    engine.type_text("Preview text", config)
    time.sleep(0.12)
    QCoreApplication.processEvents()

    assert engine.confirm_preview() is True
    if engine._scheduler._active_worker:
        for _ in range(100):
            if not engine._scheduler._active_worker.isRunning():
                break
            time.sleep(0.05)
            QCoreApplication.processEvents()

    # Test cancel preview facade call
    _job2 = engine.type_text("Cancel preview text", config)
    time.sleep(0.12)
    QCoreApplication.processEvents()

    assert engine.cancel_preview() is True
    if engine._scheduler._active_worker:
        for _ in range(100):
            if not engine._scheduler._active_worker.isRunning():
                break
            time.sleep(0.05)
            QCoreApplication.processEvents()

    # Test set_default_config & clear_queue facade calls
    engine.set_default_config(TypingConfig(speed_wpm=90.0))
    assert engine.default_config.speed_wpm == 90.0
    assert engine.clear_queue() == 0
    assert engine.queue.size() == 0


@pytest.mark.unit
def test_windows_key_input_sender_utf16_surrogate_pairs() -> None:
    """Verify WindowsKeyInputSender correctly converts characters into 16-bit UTF-16 code units."""
    sender = WindowsKeyInputSender()
    captured_scans: list[int] = []

    def mock_send_input(count: int, ptr: Any, _size: int) -> int:
        inputs = ctypes.cast(ptr, ctypes.POINTER(INPUT * 2)).contents
        captured_scans.append(inputs[0].union.ki.wScan)
        return count

    mock_target = TargetInfo(
        window_title="Test Target",
        process_name="notepad.exe",
        control_type="Edit",
        hwnd_window=100,
        hwnd_control=200,
    )

    if sys.platform == "win32" and sender._user32:
        original_send_input = sender._user32.SendInput
        sender._user32.SendInput = mock_send_input
        try:
            multilingual_test_cases = [
                ("Hello", ["0x48", "0x65", "0x6c", "0x6c", "0x6f"]),
                ("❤️", ["0x2764", "0xfe0f"]),
                ("🚀", ["0xd83d", "0xde80"]),
                ("😊", ["0xd83d", "0xde0a"]),
                ("😂", ["0xd83d", "0xde02"]),
                ("👨‍💻", ["0xd83d", "0xdc68", "0x200d", "0xd83d", "0xdcbb"]),
                ("🇮🇳", ["0xd83c", "0xddee", "0xd83c", "0xddf3"]),
                ("مرحبا", ["0x645", "0x631", "0x62d", "0x628", "0x627"]),
                ("नमस्ते", ["0x928", "0x92e", "0x938", "0x94d", "0x924", "0x947"]),
                ("你好", ["0x4f60", "0x597d"]),
                ("こんにちは", ["0x3053", "0x3093", "0x306b", "0x3061", "0x306f"]),
            ]

            for char_input, expected_wscans in multilingual_test_cases:
                captured_scans.clear()
                sender.send_char(char_input, mock_target)
                hex_scans = [hex(s) for s in captured_scans]
                assert hex_scans == expected_wscans, (
                    f"Failed for '{char_input}': got {hex_scans}, expected {expected_wscans}"
                )
                for scan in captured_scans:
                    assert 0 <= scan <= 0xFFFF, f"wScan {hex(scan)} out of 16-bit WORD bounds!"
        finally:
            sender._user32.SendInput = original_send_input


@pytest.mark.unit
def test_humanized_rhythm_plan_generation() -> None:
    """Verify Rule 1 (1s word pause) and Rule 2 (2 chars -> 0.5s pause -> rest of word)."""
    simulator = HumanTypingSimulator()
    config = TypingConfig(
        humanized_rhythm_enabled=True,
        mid_word_pause_ms=500.0,
        word_pause_ms=1000.0,
        fast_char_delay_ms=25.0,
        mistake_probability=0.0,
    )

    plan = simulator.generate_plan("Batman Overlay", config)

    pauses = [s.delay_ms for s in plan if s.action_type == TypingAction.PAUSE]
    assert 500.0 in pauses
    assert 1000.0 in pauses

    first_500_idx = next(i for i, s in enumerate(plan) if s.delay_ms == 500.0)
    typed_before_first_pause = [
        s.char for s in plan[:first_500_idx] if s.action_type == TypingAction.TYPE_CHAR
    ]
    assert typed_before_first_pause == ["B", "a"]
