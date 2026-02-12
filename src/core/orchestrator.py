"""Orchestrator: 스케줄러, 큐잉, 모니터링 시스템."""

from __future__ import annotations

import asyncio
import contextlib
import signal
import sys
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

import schedule

try:
    import structlog

    logger = structlog.get_logger(__name__)
except ImportError:
    import logging

    logger = logging.getLogger(__name__)

from src.core.models import ChannelType


class JobStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


@dataclass
class JobRecord:
    job_id: str
    channel: str
    status: JobStatus
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error: str | None = None
    retries: int = 0
    result: Any = None


class OrchestratorState(Enum):
    STOPPED = "stopped"
    RUNNING = "running"
    STOPPING = "stopping"


class Orchestrator:
    DEFAULT_SCHEDULES = {
        "horror": "09:00",
        "facts": "12:00",
        "finance": "15:00",
    }

    def __init__(
        self,
        max_concurrent: int = 2,
        max_retries: int = 3,
        retry_delay: float = 60.0,
        dry_run: bool = False,
    ):
        self.max_concurrent = max_concurrent
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.dry_run = dry_run

        self._state = OrchestratorState.STOPPED
        self._queue: asyncio.Queue[JobRecord] = asyncio.Queue()
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._jobs: dict[str, JobRecord] = {}
        self._stats: dict[str, dict[str, int]] = defaultdict(
            lambda: {"completed": 0, "failed": 0, "total": 0}
        )
        self._workers: list[asyncio.Task] = []
        self._scheduler_task: asyncio.Task | None = None
        self._pipelines: dict[str, Any] = {}

    def register_pipeline(self, channel: str, pipeline: Any):
        self._pipelines[channel] = pipeline
        logger.info("pipeline_registered", channel=channel)

    def _get_pipeline(self, channel: str) -> Any:
        if channel not in self._pipelines:
            self._lazy_load_pipeline(channel)
        return self._pipelines.get(channel)

    def _lazy_load_pipeline(self, channel: str):
        try:
            if channel == "horror":
                from src.channels.horror import create_pipeline

                self._pipelines[channel] = create_pipeline()
            elif channel == "facts":
                from src.channels.facts import create_pipeline

                self._pipelines[channel] = create_pipeline()
            elif channel == "finance":
                from src.channels.finance import create_pipeline

                self._pipelines[channel] = create_pipeline()
        except ImportError as e:
            logger.warning("pipeline_import_failed", channel=channel, error=str(e))

    async def enqueue(self, channel: str, priority: int = 0) -> str:
        job_id = str(uuid.uuid4())[:8]
        job = JobRecord(job_id=job_id, channel=channel, status=JobStatus.PENDING)
        self._jobs[job_id] = job
        await self._queue.put(job)
        self._stats[channel]["total"] += 1
        logger.info("job_enqueued", job_id=job_id, channel=channel)
        return job_id

    async def _process_job(self, job: JobRecord):
        async with self._semaphore:
            job.status = JobStatus.RUNNING
            job.started_at = datetime.now(timezone.utc)
            logger.info("job_started", job_id=job.job_id, channel=job.channel)

            try:
                if self.dry_run:
                    await self._simulate_job(job)
                else:
                    await self._execute_job(job)

                job.status = JobStatus.COMPLETED
                job.completed_at = datetime.now(timezone.utc)
                self._stats[job.channel]["completed"] += 1
                logger.info(
                    "job_completed",
                    job_id=job.job_id,
                    channel=job.channel,
                    duration=(job.completed_at - job.started_at).seconds,
                )
            except Exception as e:
                await self._handle_job_failure(job, e)

    async def _execute_job(self, job: JobRecord):
        pipeline = self._get_pipeline(job.channel)
        if not pipeline:
            raise ValueError(f"No pipeline for channel: {job.channel}")
        job.result = await pipeline.run(ChannelType(job.channel))

    async def _simulate_job(self, job: JobRecord):
        logger.info("dry_run_simulation", job_id=job.job_id, channel=job.channel)
        await asyncio.sleep(2)
        job.result = {"dry_run": True, "channel": job.channel}

    async def _handle_job_failure(self, job: JobRecord, error: Exception):
        job.retries += 1
        job.error = str(error)
        logger.error("job_failed", job_id=job.job_id, error=str(error), retry=job.retries)

        if job.retries < self.max_retries:
            job.status = JobStatus.RETRYING
            await asyncio.sleep(self.retry_delay * job.retries)
            await self._queue.put(job)
        else:
            job.status = JobStatus.FAILED
            job.completed_at = datetime.now(timezone.utc)
            self._stats[job.channel]["failed"] += 1

    async def _worker(self, worker_id: int):
        logger.info("worker_started", worker_id=worker_id)
        while self._state == OrchestratorState.RUNNING:
            try:
                job = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                await self._process_job(job)
                self._queue.task_done()
            except TimeoutError:
                continue
            except asyncio.CancelledError:
                break
        logger.info("worker_stopped", worker_id=worker_id)

    def _setup_schedules(self, schedules: dict[str, str] | None = None):
        schedule.clear()
        schedules = schedules or self.DEFAULT_SCHEDULES
        for channel, time_str in schedules.items():
            schedule.every().day.at(time_str).do(
                lambda ch=channel: asyncio.create_task(self.enqueue(ch))
            )
            logger.info("schedule_registered", channel=channel, time=time_str)

    async def _scheduler_loop(self):
        logger.info("scheduler_started")
        while self._state == OrchestratorState.RUNNING:
            schedule.run_pending()
            await asyncio.sleep(1)
        logger.info("scheduler_stopped")

    async def start(self, schedules: dict[str, str] | None = None):
        if self._state == OrchestratorState.RUNNING:
            logger.warning("orchestrator_already_running")
            return

        self._state = OrchestratorState.RUNNING
        logger.info(
            "orchestrator_starting", max_concurrent=self.max_concurrent, dry_run=self.dry_run
        )

        # Setup signal handlers within the running event loop
        if sys.platform != "win32":
            loop = asyncio.get_running_loop()
            for sig in (signal.SIGTERM, signal.SIGINT):
                loop.add_signal_handler(sig, lambda: asyncio.create_task(self.stop()))

        self._workers = [asyncio.create_task(self._worker(i)) for i in range(self.max_concurrent)]
        self._setup_schedules(schedules)
        self._scheduler_task = asyncio.create_task(self._scheduler_loop())

        logger.info("orchestrator_started")

    async def stop(self):
        if self._state != OrchestratorState.RUNNING:
            return

        self._state = OrchestratorState.STOPPING
        logger.info("orchestrator_stopping")

        if self._scheduler_task:
            self._scheduler_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._scheduler_task

        for worker in self._workers:
            worker.cancel()
        await asyncio.gather(*self._workers, return_exceptions=True)

        self._state = OrchestratorState.STOPPED
        logger.info("orchestrator_stopped")

    def status(self) -> dict[str, Any]:
        pending = sum(1 for j in self._jobs.values() if j.status == JobStatus.PENDING)
        running = sum(1 for j in self._jobs.values() if j.status == JobStatus.RUNNING)

        return {
            "state": self._state.value,
            "queue_size": self._queue.qsize(),
            "pending_jobs": pending,
            "running_jobs": running,
            "total_jobs": len(self._jobs),
            "stats": dict(self._stats),
            "workers": len(self._workers),
            "dry_run": self.dry_run,
        }

    def get_job(self, job_id: str) -> JobRecord | None:
        return self._jobs.get(job_id)

    def get_recent_jobs(self, limit: int = 10) -> list[JobRecord]:
        return sorted(self._jobs.values(), key=lambda j: j.created_at, reverse=True)[:limit]

    async def run_once(self, channel: str) -> str:
        job_id = await self.enqueue(channel)
        job = self._jobs[job_id]
        await self._process_job(job)
        return job_id

    async def run_all(self) -> list[str]:
        job_ids = []
        for channel in self._pipelines.keys() or ["horror", "facts", "finance"]:
            job_id = await self.enqueue(channel)
            job_ids.append(job_id)

        await self._queue.join()
        return job_ids


_orchestrator: Orchestrator | None = None


def get_orchestrator(**kwargs) -> Orchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = Orchestrator(**kwargs)
    return _orchestrator


def reset_orchestrator():
    global _orchestrator
    _orchestrator = None
