"""Typing scheduler and worker thread pool manager for Human Typing Engine."""

import threading
from typing import Any

from loguru import logger
from PySide6.QtCore import QObject

from src.typing.config import TypingConfig
from src.typing.events import TypingSignals
from src.typing.interfaces import IKeyInputSender, ITargetAcquirer, ITypingSimulator
from src.typing.queue import TypingJob, TypingQueue
from src.typing.worker import TypingWorker


class TypingScheduler(QObject):
    """Orchestrates job queues, worker thread lifecycles, and emergency aborts."""

    def __init__(
        self,
        signals: TypingSignals | None = None,
        target_acquirer: ITargetAcquirer | None = None,
        input_sender: IKeyInputSender | None = None,
        simulator: ITypingSimulator | None = None,
        parent: Any = None,
    ) -> None:
        super().__init__(parent)
        self._signals = signals or TypingSignals(self)
        self._target_acquirer = target_acquirer
        self._input_sender = input_sender
        self._simulator = simulator

        self._queue = TypingQueue()
        self._active_worker: TypingWorker | None = None
        self._lock = threading.Lock()

        # Connect internal worker completion hook
        self._signals.completed.connect(self._on_worker_finished)
        self._signals.cancelled.connect(self._on_worker_finished)
        self._signals.target_validation_failed.connect(self._on_worker_finished)

    @property
    def signals(self) -> TypingSignals:
        return self._signals

    @property
    def queue(self) -> TypingQueue:
        return self._queue

    def submit_job(self, text: str, config: TypingConfig | None = None) -> str:
        """Submit a new typing job to the scheduler."""
        cfg = config or TypingConfig()
        job = TypingJob(text=text, config=cfg)
        self._queue.push(job)
        logger.info(f"Submitted typing job '{job.job_id}' ({len(text)} chars) to scheduler.")

        self._process_next_job()
        return job.job_id

    def pause_current_job(self) -> bool:
        """Pause currently executing typing job."""
        with self._lock:
            if self._active_worker and self._active_worker.isRunning():
                self._active_worker.pause()
                return True
            return False

    def resume_current_job(self) -> bool:
        """Resume currently paused typing job."""
        with self._lock:
            if self._active_worker and self._active_worker.isRunning():
                self._active_worker.resume()
                return True
            return False

    def cancel_current_job(self, reason: str = "User cancelled") -> bool:
        """Cancel active job."""
        with self._lock:
            if self._active_worker and self._active_worker.isRunning():
                self._active_worker.cancel(reason)
                return True
            return False

    def emergency_abort(self) -> bool:
        """Trigger immediate emergency abort (<50ms response time).

        Cancels active worker, clears job queue, and stops all operations.
        """
        logger.warning("TypingScheduler: EMERGENCY ABORT TRIGGERED!")
        with self._lock:
            # 1. Clear pending queue
            cleared_count = self._queue.clear(reason="Emergency Abort Hotkey (ESC)")

            # 2. Cancel active worker
            if self._active_worker and self._active_worker.isRunning():
                self._active_worker.emergency_abort()
                logger.info(
                    f"Emergency abort sent to active worker. Cleared {cleared_count} queued jobs."
                )
                return True
            return False

    def confirm_preview(self) -> bool:
        """Confirm target preview for active worker."""
        with self._lock:
            if self._active_worker and self._active_worker.isRunning():
                self._active_worker.confirm_preview()
                return True
            return False

    def _process_next_job(self) -> None:
        """Pop and launch the next job in queue if no worker is running."""
        with self._lock:
            if self._active_worker and self._active_worker.isRunning():
                return

            job = self._queue.pop()
            if job is None:
                return

            worker = TypingWorker(
                job=job,
                signals=self._signals,
                target_acquirer=self._target_acquirer,
                input_sender=self._input_sender,
                simulator=self._simulator,
                parent=self,
            )
            self._active_worker = worker
            worker.start()
            logger.info(f"Started worker for typing job '{job.job_id}'.")

    def _on_worker_finished(self, job_id: str, *_args: Any) -> None:
        """Worker completion/cancel callback -> process next job in queue."""
        logger.info(f"TypingScheduler worker finished for job '{job_id}'.")
        self._process_next_job()
