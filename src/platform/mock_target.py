"""Deterministic MockTargetAcquirer and MockKeyInputSender for unit testing."""

from src.platform.models import TargetInfo, ValidationResult
from src.platform.windows_target import WindowsTargetAcquirer


class MockTargetAcquirer:
    """Mock target acquirer for unit testing without interactive OS windows."""

    def __init__(
        self,
        target_info: TargetInfo | None = None,
        is_valid: bool = True,
        failure_reason: str = "",
    ) -> None:
        self.mock_target = target_info or TargetInfo(
            window_title="Notepad - Test.txt",
            process_name="notepad.exe",
            control_type="Edit",
            hwnd_window=1001,
            hwnd_control=2002,
            is_editable=True,
        )
        self.is_valid = is_valid
        self.failure_reason = failure_reason or "Target validation failed in mock test."
        self.acquire_count = 0
        self._win_acquirer = WindowsTargetAcquirer()

    def get_foreground_target(self) -> TargetInfo | None:
        self.acquire_count += 1
        return self.mock_target

    def validate_target(self, target_info: TargetInfo | None) -> ValidationResult:
        if not self.is_valid or target_info is None:
            return ValidationResult.failure(self.failure_reason, target_info)
        return self._win_acquirer.validate_target(target_info)

    def acquire_and_validate_target(self) -> ValidationResult:
        target = self.get_foreground_target()
        return self.validate_target(target)


class MockKeyInputSender:
    """Mock key input sender capturing sent keystrokes for test assertions."""

    def __init__(self) -> None:
        self.sent_chars: list[str] = []
        self.sent_backspaces: int = 0
        self.sent_pastes: list[str] = []

    def send_char(self, char: str, _target: TargetInfo) -> bool:
        self.sent_chars.append(char)
        return True

    def send_backspace(self, _target: TargetInfo) -> bool:
        self.sent_backspaces += 1
        return True

    def send_paste_chunk(self, chunk: str, _target: TargetInfo) -> bool:
        self.sent_pastes.append(chunk)
        return True
