"""Thread-safe typing job queue implementation for Human Typing Engine."""

import queue
import threading
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum

from src.typing.config import TypingConfig
from src.typing.target import TargetInfo


class JobStatus(StrEnum):
    """Status enumeration for typing jobs."""

    QUEUED = "queued"
    COUNTDOWN = "countdown"
    TARGET_ACQUISITION = "target_acquisition"
    PREVIEW_WAIT = "preview_wait"
    TYPING = "typing"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


@dataclass
class TypingJob:
    """Represents a queued typing job."""

    text: str
    config: TypingConfig
    job_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    priority: int = 10  # Lower number = higher priority
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    status: JobStatus = JobStatus.QUEUED
    target_info: TargetInfo | None = None
    cancellation_reason: str | None = None


class TypingQueue:
    """Thread-safe FIFO and priority queue for typing jobs."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._queue: queue.PriorityQueue[tuple[int, datetime, TypingJob]] = queue.PriorityQueue()
        self._jobs: dict[str, TypingJob] = {}

    def push(self, job: TypingJob) -> None:
        """Add a job to the thread-safe queue."""
        with self._lock:
            self._jobs[job.job_id] = job
            self._queue.put((job.priority, job.created_at, job))

    def pop(self) -> TypingJob | None:
        """Pop the next highest-priority job from the queue."""
        with self._lock:
            while not self._queue.empty():
                _, _, job = self._queue.get()
                if job.status == JobStatus.QUEUED:
                    return job
            return None

    def peek(self) -> TypingJob | None:
        """Peek at the next job in queue without popping."""
        with self._lock:
            if not self._queue.empty():
                # PriorityQueue internal queue list access under lock
                items = sorted(self._queue.queue, key=lambda x: (x[0], x[1]))
                for _, _, job in items:
                    if job.status == JobStatus.QUEUED:
                        return job
            return None

    def get_job(self, job_id: str) -> TypingJob | None:
        """Retrieve a job by ID."""
        with self._lock:
            return self._jobs.get(job_id)

    def cancel_job(self, job_id: str, reason: str = "User cancelled") -> bool:
        """Cancel a specific queued or active job."""
        with self._lock:
            job = self._jobs.get(job_id)
            if job and job.status not in (
                JobStatus.COMPLETED,
                JobStatus.CANCELLED,
                JobStatus.FAILED,
            ):
                job.status = JobStatus.CANCELLED
                job.cancellation_reason = reason
                return True
            return False

    def clear(self, reason: str = "Queue cleared") -> int:
        """Clear all pending jobs from the queue."""
        count = 0
        with self._lock:
            while not self._queue.empty():
                _, _, job = self._queue.get()
                if job.status in (JobStatus.QUEUED, JobStatus.COUNTDOWN, JobStatus.PREVIEW_WAIT):
                    job.status = JobStatus.CANCELLED
                    job.cancellation_reason = reason
                    count += 1
        return count

    def size(self) -> int:
        """Return count of active queued jobs."""
        with self._lock:
            return sum(1 for j in self._jobs.values() if j.status == JobStatus.QUEUED)
