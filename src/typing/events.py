"""Event models and Qt Signal definitions for Human Typing Engine."""

from dataclasses import dataclass
from enum import StrEnum

from PySide6.QtCore import QObject, Signal


class TypingAction(StrEnum):
    """Enumeration of typing step action types."""

    TYPE_CHAR = "type_char"
    BACKSPACE = "backspace"
    PAUSE = "pause"
    PASTE_CHUNK = "paste_chunk"


@dataclass(frozen=True)
class TypingStep:
    """Represents a single atomic step in a simulated typing plan."""

    char: str
    action_type: TypingAction
    delay_ms: float


class TypingSignals(QObject):
    """Qt Signals container for Human Typing Engine events."""

    countdown_started = Signal(str, float)  # (job_id, duration_seconds)
    countdown_tick = Signal(str, int)  # (job_id, remaining_seconds)
    countdown_cancelled = Signal(str, str)  # (job_id, reason)
    target_acquired = Signal(
        str, object, int, float
    )  # (job_id, TargetInfo, char_count, est_seconds)
    target_validation_failed = Signal(str, str)  # (job_id, reason)
    preview_requested = Signal(
        str, object, int, float
    )  # (job_id, TargetInfo, char_count, est_seconds)
    typing_started = Signal(str, str)  # (job_id, text)
    typing_progress = Signal(str, int, int, float)  # (job_id, current_index, total_count, percent)
    character_typed = Signal(str, str, str)  # (job_id, char, action_type)
    paused = Signal(str)  # (job_id)
    resumed = Signal(str)  # (job_id)
    cancelled = Signal(str, str)  # (job_id, reason)
    completed = Signal(str, float)  # (job_id, duration_seconds)
    error_occurred = Signal(str, str)  # (job_id, error_message)
