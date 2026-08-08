"""Protocol interface definitions for platform target acquirer and input sender."""

from typing import Protocol, runtime_checkable

from src.platform.models import TargetInfo, ValidationResult


@runtime_checkable
class ITargetAcquirer(Protocol):
    """Interface for OS foreground window and focused control target acquisition."""

    def get_foreground_target(self) -> TargetInfo | None: ...

    def validate_target(self, target_info: TargetInfo | None) -> ValidationResult: ...

    def acquire_and_validate_target(self) -> ValidationResult: ...


@runtime_checkable
class IKeyInputSender(Protocol):
    """Interface for sending OS keystrokes or text chunks to focused input controls."""

    def send_char(self, char: str, target: TargetInfo) -> bool: ...

    def send_backspace(self, target: TargetInfo) -> bool: ...

    def send_paste_chunk(self, chunk: str, target: TargetInfo) -> bool: ...
