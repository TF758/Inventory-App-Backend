from datetime import timedelta

from django.test import TestCase, override_settings
from django.utils import timezone

from reporting.models.reports import ReportJob
from reporting.services.job_state import claim_job, prepare_job_retry
from users.factories.user_factories import UserFactory


@override_settings(
    JOB_STALE_AFTER_SECONDS=60,
    JOB_DISPATCH_GRACE_SECONDS=10,
    JOB_MAX_ATTEMPTS=3,
)
class ReportJobLeaseTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()

    def make_job(self, **overrides):
        values = {
            "user": self.user,
            "report_type": ReportJob.ReportType.USER_SUMMARY,
            "params": {},
        }
        values.update(overrides)
        return ReportJob.objects.create(**values)

    def test_pending_job_is_claimed_once(self):
        job = self.make_job()

        claim = claim_job(job.id, "task-one")

        self.assertTrue(claim.claimed)
        job.refresh_from_db()
        self.assertEqual(job.status, ReportJob.Status.RUNNING)
        self.assertEqual(job.task_id, "task-one")
        self.assertEqual(job.attempt_count, 1)
        self.assertIsNotNone(job.heartbeat_at)

    def test_active_job_rejects_a_different_delivery(self):
        job = self.make_job(
            status=ReportJob.Status.RUNNING,
            task_id="task-one",
            attempt_count=1,
            started_at=timezone.now(),
            heartbeat_at=timezone.now(),
        )

        claim = claim_job(job.id, "task-two")

        self.assertFalse(claim.claimed)
        self.assertEqual(claim.reason, "duplicate")
        job.refresh_from_db()
        self.assertEqual(job.task_id, "task-one")
        self.assertEqual(job.attempt_count, 1)

    def test_same_task_id_can_resume_after_redelivery(self):
        job = self.make_job(
            status=ReportJob.Status.RUNNING,
            task_id="task-one",
            attempt_count=1,
            started_at=timezone.now(),
            heartbeat_at=timezone.now(),
        )

        claim = claim_job(job.id, "task-one")

        self.assertTrue(claim.claimed)
        self.assertEqual(claim.reason, "redelivery")
        job.refresh_from_db()
        self.assertEqual(job.attempt_count, 1)

    def test_stale_lease_can_be_taken_over(self):
        stale_at = timezone.now() - timedelta(minutes=5)
        job = self.make_job(
            status=ReportJob.Status.RUNNING,
            task_id="lost-task",
            attempt_count=1,
            started_at=stale_at,
            heartbeat_at=stale_at,
        )

        claim = claim_job(job.id, "replacement-task")

        self.assertTrue(claim.claimed)
        job.refresh_from_db()
        self.assertEqual(job.task_id, "replacement-task")
        self.assertEqual(job.attempt_count, 2)

    def test_retry_keeps_the_execution_lease_reserved(self):
        job = self.make_job()
        claim_job(job.id, "task-one")

        self.assertTrue(prepare_job_retry(job.id, "task-one"))

        job.refresh_from_db()
        self.assertEqual(job.status, ReportJob.Status.RUNNING)
        self.assertEqual(job.task_id, "task-one")
        self.assertIsNotNone(job.started_at)
        self.assertIsNotNone(job.heartbeat_at)
        self.assertEqual(job.attempt_count, 2)

    def test_worker_redelivery_consumes_an_attempt(self):
        job = self.make_job(
            status=ReportJob.Status.RUNNING,
            task_id="task-one",
            attempt_count=1,
            started_at=timezone.now(),
            heartbeat_at=timezone.now(),
        )

        claim = claim_job(
            job.id,
            "task-one",
            redelivered=True,
        )

        self.assertTrue(claim.claimed)
        job.refresh_from_db()
        self.assertEqual(job.attempt_count, 2)

    def test_worker_redelivery_stops_at_attempt_limit(self):
        job = self.make_job(
            status=ReportJob.Status.RUNNING,
            task_id="task-one",
            attempt_count=3,
            started_at=timezone.now(),
            heartbeat_at=timezone.now(),
        )

        claim = claim_job(
            job.id,
            "task-one",
            redelivered=True,
        )

        self.assertFalse(claim.claimed)
        self.assertEqual(claim.reason, "attempts_exhausted")
        job.refresh_from_db()
        self.assertEqual(job.status, ReportJob.Status.FAILED)

    def test_attempt_limit_moves_job_to_public_failure_state(self):
        job = self.make_job(attempt_count=3)

        claim = claim_job(job.id, "task-four")

        self.assertFalse(claim.claimed)
        self.assertEqual(claim.reason, "attempts_exhausted")
        job.refresh_from_db()
        self.assertEqual(job.status, ReportJob.Status.FAILED)
        self.assertEqual(job.error, "Report generation failed.")
        self.assertEqual(job.task_id, "")
