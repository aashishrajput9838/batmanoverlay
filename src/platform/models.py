"""Target acquisition and validation data models for platform layer."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class TargetInfo:
    """Dataclass holding information about the target window and focused input control."""

    window_title: str
    process_name: str
    control_type: str
    hwnd_window: int
    hwnd_control: int
    is_editable: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "window_title": self.window_title,
            "process_name": self.process_name,
            "control_type": self.control_type,
            "hwnd_window": self.hwnd_window,
            "hwnd_control": self.hwnd_control,
            "is_editable": self.is_editable,
        }


@dataclass(frozen=True)
class ValidationResult:
    """Dataclass holding the outcome of dynamic target validation."""

    is_valid: bool
    reason: str
    target_info: TargetInfo | None = None

    @classmethod
    def success(cls, target_info: TargetInfo) -> "ValidationResult":
        return cls(
            is_valid=True, reason="Target control is valid and editable.", target_info=target_info
        )

    @classmethod
    def failure(cls, reason: str, target_info: TargetInfo | None = None) -> "ValidationResult":
        return cls(is_valid=False, reason=reason, target_info=target_info)
