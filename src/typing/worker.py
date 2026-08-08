"""Worker thread execution engine for Human Typing Engine."""

import time
from typing import Any

from loguru import logger
from PySide6.QtCore import QMutex, QThread, QWaitCondition

from src.typing.config import TypingConfig
from src.typing.events import TypingAction, TypingSignals
from src.typing.interfaces import IKeyInputSender, ITargetAcquirer, ITypingSimulator
from src.typing.queue import JobStatus, TypingJob
from src.typing.simulator import HumanTypingSimulator
from src.typing.target import TargetInfo


class TypingWorker(QThread):
    """QThread worker driving countdown, target acquisition, preview, and step execution."""

    def __init__(
        self,
        job: TypingJob,
        signals: TypingSignals,
        target_acquirer: ITargetAcquirer | None = None,
        input_sender: IKeyInputSender | None = None,
        simulator: ITypingSimulator | None = None,
        parent: Any = None,
    ) -> None:
        super().__init__(parent)
        self.job = job
        self.signals = signals

        if target_acquirer is None or input_sender is None:
            from src.platform import get_platform_input_sender, get_platform_target_acquirer

            target_acquirer = target_acquirer or get_platform_target_acquirer()
            input_sender = input_sender or get_platform_input_sender()

        self._acquirer = target_acquirer
        self._sender = input_sender
        self._simulator = simulator or HumanTypingSimulator()

        self._mutex = QMutex()
        self._pause_condition = QWaitCondition()

        self._is_paused = False
        self._is_cancelled = False
        self._is_aborted = False
        self._preview_confirmed = not job.config.show_preview_dialog
        self._cancel_reason = "Cancelled"

    def is_paused(self) -> bool:
        return self._is_paused

    def is_cancelled(self) -> bool:
        return self._is_cancelled or self._is_aborted

    def pause(self) -> None:
        """Pause worker thread execution."""
        self._mutex.lock()
        self._is_paused = True
        self.job.status = JobStatus.PAUSED
        self._mutex.unlock()
        self.signals.paused.emit(self.job.job_id)
        logger.info(f"TypingWorker job '{self.job.job_id}' paused.")

    def resume(self) -> None:
        """Resume paused worker thread execution."""
        self._mutex.lock()
        self._is_paused = False
        self.job.status = JobStatus.TYPING
        self._pause_condition.wakeAll()
        self._mutex.unlock()
        self.signals.resumed.emit(self.job.job_id)
        logger.info(f"TypingWorker job '{self.job.job_id}' resumed.")

    def cancel(self, reason: str = "User cancelled") -> None:
        """Cancel worker execution immediately (<5ms latency)."""
        self._mutex.lock()
        self._is_cancelled = True
        self._cancel_reason = reason
        self.job.status = JobStatus.CANCELLED
        self.job.cancellation_reason = reason
        if self._is_paused:
            self._is_paused = False
            self._pause_condition.wakeAll()
        self._mutex.unlock()

    def emergency_abort(self) -> None:
        """Trigger immediate emergency abort (<50ms response)."""
        self._mutex.lock()
        self._is_aborted = True
        self._is_cancelled = True
        self._cancel_reason = "Emergency Abort Hotkey (ESC)"
        self.job.status = JobStatus.CANCELLED
        if self._is_paused:
            self._is_paused = False
            self._pause_condition.wakeAll()
        self._mutex.unlock()
        logger.warning(f"EMERGENCY ABORT triggered for job '{self.job.job_id}'.")

    def confirm_preview(self) -> None:
        """User confirmed target preview dialog."""
        self._mutex.lock()
        self._preview_confirmed = True
        self._mutex.unlock()

    def run(self) -> None:
        """Main QThread execution pipeline."""
        start_time = time.perf_counter()

        if not self._run_countdown_phase():
            return

        target_info = self._run_target_acquisition_phase()
        if target_info is None:
            return

        if not self._run_preview_phase(target_info):
            return

        if not self._run_typing_plan_phase(target_info):
            return

        self.job.status = JobStatus.COMPLETED
        elapsed = round(time.perf_counter() - start_time, 2)
        self.signals.completed.emit(self.job.job_id, elapsed)
        logger.info(f"Job '{self.job.job_id}' completed successfully in {elapsed}s.")

    def _run_countdown_phase(self) -> bool:
        config: TypingConfig = self.job.config
        job_id: str = self.job.job_id

        if config.start_delay_seconds <= 0:
            return True

        self.job.status = JobStatus.COUNTDOWN
        duration = config.start_delay_seconds
        self.signals.countdown_started.emit(job_id, duration)
        logger.info(f"Job '{job_id}' countdown started for {duration}s.")

        remaining = int(duration)
        while remaining > 0:
            if self._check_cancel_or_abort():
                return False

            self.signals.countdown_tick.emit(job_id, remaining)
            for _ in range(20):
                if self._check_cancel_or_abort():
                    return False
                self.msleep(50)
            remaining -= 1

        self.signals.countdown_tick.emit(job_id, 0)
        return True

    def _run_target_acquisition_phase(self) -> TargetInfo | None:
        if self._check_cancel_or_abort():
            return None

        job_id: str = self.job.job_id
        config: TypingConfig = self.job.config
        self.job.status = JobStatus.TARGET_ACQUISITION
        val_result = self._acquirer.acquire_and_validate_target()

        if not val_result.is_valid or val_result.target_info is None:
            self.job.status = JobStatus.FAILED
            err_msg = val_result.reason
            logger.error(f"Job '{job_id}' Target Validation Failed: {err_msg}")
            self.signals.target_validation_failed.emit(job_id, err_msg)
            self.signals.error_occurred.emit(job_id, err_msg)
            return None

        target_info: TargetInfo = val_result.target_info
        self.job.target_info = target_info
        char_count = len(self.job.text)
        est_seconds = config.calculate_estimated_duration_seconds(char_count)

        self.signals.target_acquired.emit(job_id, target_info, char_count, est_seconds)
        logger.info(
            f"Job '{job_id}' Target Acquired: Window='{target_info.window_title}', "
            f"Process='{target_info.process_name}', Control='{target_info.control_type}'"
        )
        return target_info

    def _run_preview_phase(self, target_info: TargetInfo) -> bool:
        config: TypingConfig = self.job.config
        job_id: str = self.job.job_id

        if not config.show_preview_dialog:
            return True

        self.job.status = JobStatus.PREVIEW_WAIT
        char_count = len(self.job.text)
        est_seconds = config.calculate_estimated_duration_seconds(char_count)
        self.signals.preview_requested.emit(job_id, target_info, char_count, est_seconds)
        logger.info(f"Job '{job_id}' waiting for user preview confirmation...")

        while not self._preview_confirmed:
            if self._check_cancel_or_abort():
                return False
            self.msleep(50)
        return True

    def _run_typing_plan_phase(self, target_info: TargetInfo) -> bool:
        if self._check_cancel_or_abort():
            return False

        config: TypingConfig = self.job.config
        job_id: str = self.job.job_id
        self.job.status = JobStatus.TYPING
        plan = self._simulator.generate_plan(self.job.text, config)
        total_steps = len(plan)

        self.signals.typing_started.emit(job_id, self.job.text)
        logger.info(f"Job '{job_id}' TypingPlan execution started ({total_steps} steps).")

        if config.initial_delay_ms > 0 and not self._high_precision_sleep(config.initial_delay_ms):
            return False

        for idx, step in enumerate(plan):
            if self._check_cancel_or_abort():
                return False

            self._handle_pause_lock()
            if self._check_cancel_or_abort():
                return False

            self._execute_step(step, target_info)

            percent = round(((idx + 1) / total_steps) * 100.0, 1)
            self.signals.character_typed.emit(job_id, step.char, step.action_type.value)
            self.signals.typing_progress.emit(job_id, idx + 1, total_steps, percent)

            if (
                step.delay_ms > 0
                and idx < total_steps - 1
                and not self._high_precision_sleep(step.delay_ms)
            ):
                return False

        return True

    def _execute_step(self, step: Any, target: TargetInfo) -> None:
        """Dispatch step to platform key input sender."""
        if step.action_type == TypingAction.TYPE_CHAR:
            self._sender.send_char(step.char, target)
        elif step.action_type == TypingAction.BACKSPACE:
            self._sender.send_backspace(target)
        elif step.action_type == TypingAction.PASTE_CHUNK:
            self._sender.send_paste_chunk(step.char, target)

    def _high_precision_sleep(self, delay_ms: float) -> bool:
        """Sleep for delay_ms while polling cancellation flag every 5ms."""
        target_time = time.perf_counter() + (delay_ms / 1000.0)
        while time.perf_counter() < target_time:
            if self._check_cancel_or_abort():
                return False
            self.msleep(5)
        return True

    def _handle_pause_lock(self) -> None:
        """Block worker thread execution if paused."""
        self._mutex.lock()
        while self._is_paused and not self._is_cancelled and not self._is_aborted:
            self._pause_condition.wait(self._mutex)
        self._mutex.unlock()

    def _check_cancel_or_abort(self) -> bool:
        """Check if worker was cancelled or aborted."""
        if self._is_cancelled or self._is_aborted:
            reason = self._cancel_reason
            self.signals.cancelled.emit(self.job.job_id, reason)
            logger.info(f"Worker for job '{self.job.job_id}' exited cleanly: {reason}")
            return True
        return False
