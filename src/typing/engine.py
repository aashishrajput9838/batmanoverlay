"""Facade class unifying configuration, scheduling, execution, and Qt signals for batmanoverlay."""

from typing import Any

from loguru import logger

from src.typing.config import TypingConfig
from src.typing.events import TypingSignals
from src.typing.interfaces import IKeyInputSender, ITargetAcquirer, ITypingSimulator
from src.typing.scheduler import TypingScheduler


class HumanTypingEngine:
    """Public Facade class for Human Typing Engine operations and event signals."""

    def __init__(
        self,
        default_config: TypingConfig | None = None,
        target_acquirer: ITargetAcquirer | None = None,
        input_sender: IKeyInputSender | None = None,
        simulator: ITypingSimulator | None = None,
        parent: Any = None,
    ) -> None:
        self._default_config = default_config or TypingConfig()
        self._scheduler = TypingScheduler(
            target_acquirer=target_acquirer,
            input_sender=input_sender,
            simulator=simulator,
            parent=parent,
        )

        logger.info("Initialized HumanTypingEngine facade API.")

    @property
    def signals(self) -> TypingSignals:
        """Access public Qt signals for typing events."""
        return self._scheduler.signals

    @property
    def queue(self) -> Any:
        """Access typing job queue."""
        return self._scheduler.queue

    @property
    def default_config(self) -> TypingConfig:
        return self._default_config

    def set_default_config(self, config: TypingConfig) -> None:
        """Update default engine configuration."""
        self._default_config = config
        logger.info(
            f"Updated default TypingConfig: speed={config.speed_wpm} WPM, "
            f"delay={config.start_delay_seconds}s."
        )

    def type_text(self, text: str, config_override: TypingConfig | None = None) -> str:
        """Submit text for human typing simulation.

        Returns:
            job_id: Unique string identifier for the submitted typing job.
        """
        cfg = config_override or self._default_config
        job_id = self._scheduler.submit_job(text, cfg)
        logger.info(f"Submitted typing job '{job_id}' via HumanTypingEngine.")
        return job_id

    def pause(self) -> bool:
        """Pause active typing execution."""
        return self._scheduler.pause_current_job()

    def resume(self) -> bool:
        """Resume active paused typing execution."""
        return self._scheduler.resume_current_job()

    def cancel(self, reason: str = "User cancelled") -> bool:
        """Cancel active typing job."""
        return self._scheduler.cancel_current_job(reason)

    def emergency_abort(self) -> bool:
        """Trigger immediate global emergency abort (<50ms response).

        Clears queue and stops active typing worker instantly.
        """
        return self._scheduler.emergency_abort()

    def confirm_preview(self) -> bool:
        """Confirm target preview modal and proceed to typing."""
        return self._scheduler.confirm_preview()

    def cancel_preview(self) -> bool:
        """Cancel target preview modal and abort job."""
        return self.cancel(reason="Preview cancelled by user")

    def clear_queue(self) -> int:
        """Clear all pending queued jobs."""
        return self._scheduler.queue.clear(reason="Queue cleared")
