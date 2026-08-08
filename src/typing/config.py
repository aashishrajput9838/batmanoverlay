"""Configuration model for Human Typing Engine."""

from typing import Annotated

from pydantic import BaseModel, Field


class TypingConfig(BaseModel):
    """Configuration settings for human typing simulation, delays, and safety rules."""

    start_delay_seconds: float = Field(
        default=10.0,
        ge=0.0,
        le=300.0,
        description="Countdown delay in seconds before target acquisition and typing starts.",
    )
    show_preview_dialog: bool = Field(
        default=False,
        description="If True, displays target confirmation dialog before sending keystrokes.",
    )
    emergency_abort_key: str = Field(
        default="Escape",
        description="Global hotkey for immediate emergency cancellation (<50ms response).",
    )
    speed_wpm: float = Field(
        default=60.0,
        gt=0.0,
        le=2000.0,
        description="Target typing speed in Words Per Minute (WPM).",
    )
    min_delay_ms: float = Field(
        default=20.0,
        ge=1.0,
        le=1000.0,
        description="Minimum delay in milliseconds between keystrokes.",
    )
    max_delay_ms: float = Field(
        default=180.0,
        ge=5.0,
        le=5000.0,
        description="Maximum delay in milliseconds between keystrokes.",
    )
    initial_delay_ms: float = Field(
        default=300.0,
        ge=0.0,
        le=10000.0,
        description="Initial pause in milliseconds before typing the first character.",
    )
    mistake_probability: Annotated[
        float, Field(ge=0.0, le=0.5, description="Probability (0.0 to 0.5) of making a typo.")
    ] = 0.03
    correction_delay_ms: float = Field(
        default=150.0,
        ge=0.0,
        le=3000.0,
        description="Pause in milliseconds before backspacing to fix a typo.",
    )
    typing_jitter: float = Field(
        default=0.25,
        ge=0.0,
        le=1.0,
        description="Random Gaussian variance factor applied to typing delays.",
    )
    enable_paste_threshold: bool = Field(
        default=True,
        description="If True, auto-pastes text exceeding threshold via Ctrl+V.",
    )
    paste_threshold_chars: int = Field(
        default=500,
        ge=10,
        le=100000,
        description="Character threshold above which text is pasted in chunks instead of typed.",
    )
    random_seed: int | None = Field(
        default=None,
        description="Optional seed for deterministic, repeatable typing tests.",
    )
    pause_key: str = Field(
        default="Pause",
        description="Hotkey key name for pausing/resuming active typing job.",
    )

    def calculate_estimated_duration_seconds(self, char_count: int) -> float:
        """Calculate estimated typing duration in seconds for a given character count."""
        if char_count >= self.paste_threshold_chars:
            return 0.5  # Instant chunk paste

        # Average words = char_count / 5
        words = char_count / 5.0
        base_seconds = (words / self.speed_wpm) * 60.0
        # Add estimated delay for typos and initial delay
        typo_overhead = (char_count * self.mistake_probability) * (
            self.correction_delay_ms / 1000.0
        )
        initial_overhead = self.initial_delay_ms / 1000.0

        return round(base_seconds + typo_overhead + initial_overhead, 2)
