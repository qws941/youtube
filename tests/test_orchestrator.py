from __future__ import annotations

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.orchestrator import (
    JobRecord,
    JobStatus,
    Orchestrator,
    OrchestratorState,
    get_orchestrator,
    reset_orchestrator,
)


class TestJobRecord:

    def test_job_record_creation(self):
        job = JobRecord(
            job_id="test-001",
            channel="horror",
            status=JobStatus.PENDING,
        )

        assert job.job_id == "test-001"
        assert job.channel == "horror"
        assert job.status == JobStatus.PENDING
        assert job.retries == 0
        assert job.error is None
        assert job.result is None
        assert isinstance(job.created_at, datetime)

    def test_job_status_values(self):
        assert JobStatus.PENDING.value == "pending"
        assert JobStatus.RUNNING.value == "running"
        assert JobStatus.COMPLETED.value == "completed"
        assert JobStatus.FAILED.value == "failed"
        assert JobStatus.RETRYING.value == "retrying"


class TestOrchestratorState:

    def test_state_values(self):
        assert OrchestratorState.STOPPED.value == "stopped"
        assert OrchestratorState.RUNNING.value == "running"
        assert OrchestratorState.STOPPING.value == "stopping"


class TestOrchestratorInit:

    def test_default_init(self):
        orch = Orchestrator()

        assert orch.max_concurrent == 2
        assert orch.max_retries == 3
        assert orch.retry_delay == 60.0
        assert orch.dry_run is False
        assert orch._state == OrchestratorState.STOPPED

    def test_custom_init(self):
        orch = Orchestrator(
            max_concurrent=4,
            max_retries=5,
            retry_delay=30.0,
            dry_run=True,
        )

        assert orch.max_concurrent == 4
        assert orch.max_retries == 5
        assert orch.retry_delay == 30.0
        assert orch.dry_run is True

    def test_default_schedules(self):
        expected = {
            "horror": "09:00",
            "facts": "12:00",
            "finance": "15:00",
        }
        assert expected == Orchestrator.DEFAULT_SCHEDULES


class TestSingleton:

    def test_get_orchestrator_returns_same_instance(self):
        reset_orchestrator()

        orch1 = get_orchestrator(dry_run=True)
        orch2 = get_orchestrator()

        assert orch1 is orch2

    def test_reset_orchestrator_clears_instance(self):
        orch1 = get_orchestrator(dry_run=True)
        reset_orchestrator()
        orch2 = get_orchestrator(dry_run=False)

        assert orch1 is not orch2
        assert orch1.dry_run is True
        assert orch2.dry_run is False


class TestEnqueue:

    @pytest.mark.asyncio
    async def test_enqueue_creates_job(self, orchestrator_dry_run: Orchestrator):
        job_id = await orchestrator_dry_run.enqueue("horror")

        assert job_id is not None
        assert len(job_id) == 8

        job = orchestrator_dry_run.get_job(job_id)
        assert job is not None
        assert job.channel == "horror"
        assert job.status == JobStatus.PENDING

    @pytest.mark.asyncio
    async def test_enqueue_increments_stats(self, orchestrator_dry_run: Orchestrator):
        await orchestrator_dry_run.enqueue("horror")
        await orchestrator_dry_run.enqueue("horror")
        await orchestrator_dry_run.enqueue("facts")

        status = orchestrator_dry_run.status()
        assert status["stats"]["horror"]["total"] == 2
        assert status["stats"]["facts"]["total"] == 1

    @pytest.mark.asyncio
    async def test_enqueue_adds_to_queue(self, orchestrator_dry_run: Orchestrator):
        await orchestrator_dry_run.enqueue("horror")
        await orchestrator_dry_run.enqueue("facts")

        assert orchestrator_dry_run._queue.qsize() == 2


class TestJobProcessing:

    @pytest.mark.asyncio
    async def test_process_job_dry_run(self, orchestrator_dry_run: Orchestrator):
        job = JobRecord(
            job_id="test-001",
            channel="horror",
            status=JobStatus.PENDING,
        )

        await orchestrator_dry_run._process_job(job)

        assert job.status == JobStatus.COMPLETED
        assert job.started_at is not None
        assert job.completed_at is not None
        assert job.result == {"dry_run": True, "channel": "horror"}

    @pytest.mark.asyncio
    async def test_process_job_with_pipeline(
        self, orchestrator_with_mock_pipeline: Orchestrator
    ):
        orchestrator_with_mock_pipeline.dry_run = False

        job = JobRecord(
            job_id="test-002",
            channel="horror",
            status=JobStatus.PENDING,
        )

        await orchestrator_with_mock_pipeline._process_job(job)

        assert job.status == JobStatus.COMPLETED
        assert job.result == {"status": "completed"}

    @pytest.mark.asyncio
    async def test_process_job_failure_triggers_retry(
        self, orchestrator_dry_run: Orchestrator
    ):
        orchestrator_dry_run.dry_run = False

        failing_pipeline = MagicMock()
        failing_pipeline.run = AsyncMock(side_effect=Exception("Test error"))
        orchestrator_dry_run.register_pipeline("horror", failing_pipeline)

        job = JobRecord(
            job_id="test-003",
            channel="horror",
            status=JobStatus.PENDING,
        )
        orchestrator_dry_run._jobs[job.job_id] = job

        await orchestrator_dry_run._process_job(job)

        assert job.status == JobStatus.RETRYING
        assert job.retries == 1
        assert job.error == "Test error"

    @pytest.mark.asyncio
    async def test_max_retries_exhausted(self, orchestrator_dry_run: Orchestrator):
        orchestrator_dry_run.dry_run = False
        orchestrator_dry_run.retry_delay = 0.01

        failing_pipeline = MagicMock()
        failing_pipeline.run = AsyncMock(side_effect=Exception("Persistent error"))
        orchestrator_dry_run.register_pipeline("horror", failing_pipeline)

        job = JobRecord(
            job_id="test-004",
            channel="horror",
            status=JobStatus.PENDING,
        )
        job.retries = 2
        orchestrator_dry_run._jobs[job.job_id] = job

        await orchestrator_dry_run._process_job(job)

        assert job.status == JobStatus.FAILED
        assert job.retries == 3


class TestSemaphoreConcurrency:

    @pytest.mark.asyncio
    async def test_semaphore_limits_concurrency(self):
        orch = Orchestrator(max_concurrent=2, dry_run=True)
        concurrent_count = 0
        max_concurrent_reached = 0

        async def track_concurrency(job: JobRecord):
            nonlocal concurrent_count, max_concurrent_reached
            async with orch._semaphore:
                concurrent_count += 1
                max_concurrent_reached = max(max_concurrent_reached, concurrent_count)
                await asyncio.sleep(0.05)
                concurrent_count -= 1

        jobs = [
            JobRecord(job_id=f"job-{i}", channel="horror", status=JobStatus.PENDING)
            for i in range(5)
        ]

        await asyncio.gather(*[track_concurrency(job) for job in jobs])

        assert max_concurrent_reached <= 2


class TestRunOnce:

    @pytest.mark.asyncio
    async def test_run_once_executes_immediately(
        self, orchestrator_dry_run: Orchestrator
    ):
        job_id = await orchestrator_dry_run.run_once("horror")

        job = orchestrator_dry_run.get_job(job_id)
        assert job is not None
        assert job.status == JobStatus.COMPLETED


class TestStatus:

    @pytest.mark.asyncio
    async def test_status_returns_correct_info(
        self, orchestrator_dry_run: Orchestrator
    ):
        await orchestrator_dry_run.enqueue("horror")
        await orchestrator_dry_run.enqueue("facts")

        status = orchestrator_dry_run.status()

        assert status["state"] == "stopped"
        assert status["queue_size"] == 2
        assert status["pending_jobs"] == 2
        assert status["running_jobs"] == 0
        assert status["total_jobs"] == 2
        assert status["dry_run"] is True


class TestGetJobs:

    @pytest.mark.asyncio
    async def test_get_job_returns_job(self, orchestrator_dry_run: Orchestrator):
        job_id = await orchestrator_dry_run.enqueue("horror")

        job = orchestrator_dry_run.get_job(job_id)

        assert job is not None
        assert job.job_id == job_id

    def test_get_job_returns_none_for_unknown(
        self, orchestrator_dry_run: Orchestrator
    ):
        job = orchestrator_dry_run.get_job("nonexistent")
        assert job is None

    @pytest.mark.asyncio
    async def test_get_recent_jobs(self, orchestrator_dry_run: Orchestrator):
        for _i in range(15):
            await orchestrator_dry_run.enqueue("horror")

        recent = orchestrator_dry_run.get_recent_jobs(limit=10)

        assert len(recent) == 10


class TestStartStop:

    @pytest.mark.asyncio
    async def test_start_creates_workers(self, orchestrator_dry_run: Orchestrator):
        await orchestrator_dry_run.start()

        try:
            assert orchestrator_dry_run._state == OrchestratorState.RUNNING
            assert len(orchestrator_dry_run._workers) == 2
            assert orchestrator_dry_run._scheduler_task is not None
        finally:
            await orchestrator_dry_run.stop()

    @pytest.mark.asyncio
    async def test_stop_gracefully_shuts_down(self, orchestrator_dry_run: Orchestrator):
        await orchestrator_dry_run.start()
        await orchestrator_dry_run.stop()

        assert orchestrator_dry_run._state == OrchestratorState.STOPPED

    @pytest.mark.asyncio
    async def test_double_start_is_noop(self, orchestrator_dry_run: Orchestrator):
        await orchestrator_dry_run.start()

        try:
            workers_before = orchestrator_dry_run._workers
            await orchestrator_dry_run.start()
            workers_after = orchestrator_dry_run._workers

            assert workers_before is workers_after
        finally:
            await orchestrator_dry_run.stop()

    @pytest.mark.asyncio
    async def test_stop_when_not_running_is_noop(
        self, orchestrator_dry_run: Orchestrator
    ):
        await orchestrator_dry_run.stop()
        assert orchestrator_dry_run._state == OrchestratorState.STOPPED


class TestPipelineRegistration:

    def test_register_pipeline(self, orchestrator_dry_run: Orchestrator):
        mock_pipeline = MagicMock()

        orchestrator_dry_run.register_pipeline("horror", mock_pipeline)

        assert "horror" in orchestrator_dry_run._pipelines
        assert orchestrator_dry_run._pipelines["horror"] is mock_pipeline

    def test_get_pipeline_returns_registered(
        self, orchestrator_dry_run: Orchestrator
    ):
        mock_pipeline = MagicMock()
        orchestrator_dry_run.register_pipeline("horror", mock_pipeline)

        retrieved = orchestrator_dry_run._get_pipeline("horror")

        assert retrieved is mock_pipeline

    def test_lazy_load_pipeline(self, orchestrator_dry_run: Orchestrator):
        with patch("src.channels.horror.create_pipeline") as mock_create:
            mock_pipeline = MagicMock()
            mock_create.return_value = mock_pipeline

            orchestrator_dry_run._lazy_load_pipeline("horror")

            assert "horror" in orchestrator_dry_run._pipelines


class TestWorkerLoop:

    @pytest.mark.asyncio
    async def test_worker_processes_queued_jobs(
        self, orchestrator_dry_run: Orchestrator
    ):
        await orchestrator_dry_run.start()

        try:
            job_id = await orchestrator_dry_run.enqueue("horror")

            await asyncio.sleep(3)

            job = orchestrator_dry_run.get_job(job_id)
            assert job is not None
            assert job.status == JobStatus.COMPLETED
        finally:
            await orchestrator_dry_run.stop()
