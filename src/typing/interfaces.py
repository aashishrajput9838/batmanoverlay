"""Protocol interface definitions for Human Typing Engine components."""

from typing import Protocol, runtime_checkable

from src.platform.protocols import IKeyInputSender, ITargetAcquirer
from src.typing.config import TypingConfig
from src.typing.events import TypingSignals, TypingStep


@runtime_checkable
class ITypingSimulator(Protocol):
    """Interface for human typing action plan generation."""

    def generate_plan(self, text: str, config: TypingConfig) -> list[TypingStep]: ...


@runtime_checkable
class ITypingWorker(Protocol):
    """Interface for executing typing jobs inside worker threads."""

    def is_running(self) -> bool: ...

    def is_paused(self) -> bool: ...

    def pause(self) -> None: ...

    def resume(self) -> None: ...

    def cancel(self, reason: str = "User cancelled") -> None: ...

    def confirm_preview(self) -> None: ...


@runtime_checkable
class ITypingQueue(Protocol):
    """Interface for thread-safe typing job queue."""

    def size(self) -> int: ...

    def clear(self, reason: str = "Queue cleared") -> int: ...


@runtime_checkable
class ITypingScheduler(Protocol):
    """Interface for managing typing job queues and worker thread lifecycles."""

    @property
    def signals(self) -> TypingSignals: ...

    def submit_job(self, text: str, config: TypingConfig | None = None) -> str: ...

    def pause_current_job(self) -> bool: ...

    def resume_current_job(self) -> bool: ...

    def cancel_current_job(self, reason: str = "User cancelled") -> bool: ...

    def emergency_abort(self) -> bool: ...

    def confirm_preview(self) -> bool: ...


__all__ = [
    "IKeyInputSender",
    "ITargetAcquirer",
    "ITypingQueue",
    "ITypingScheduler",
    "ITypingSimulator",
    "ITypingWorker",
]
