from django.test import TestCase
from django.utils import timezone
from datetime import timedelta

from analytics.models.metrics import DailyReturnMetrics
from analytics.services.snapshots import generate_daily_return_metrics
from assignments.models.asset_assignment import ReturnRequest, ReturnRequestItem
from sites.factories.site_factories import RoomFactory
from users.factories.user_factories import UserFactory
from sites.models import Room
import datetime

class TestDailyReturnMetrics(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.now = timezone.now()
        cls.today = timezone.localdate()
        cls.room = RoomFactory()
        

    # -------------------------
    # Helpers
    # -------------------------

    def create_request(self, status=ReturnRequest.Status.PENDING, requested_at=None, processed_at=None):
        req = ReturnRequest.objects.create(
            requester=self.user,
            status=status,
        )

        if requested_at is not None or processed_at is not None:
            ReturnRequest.objects.filter(pk=req.pk).update(
                requested_at=requested_at or req.requested_at,
                processed_at=processed_at
            )
            req.refresh_from_db()

        return req

    def create_item(self, request, status=ReturnRequestItem.Status.PENDING, item_type=ReturnRequestItem.ItemType.EQUIPMENT):
        return ReturnRequestItem.objects.create(
            return_request=request,
            status=status,
            item_type=item_type,
            room=self.room,  # ✅ correct
        )
    # -------------------------
    # Core aggregation tests
    # -------------------------

    def test_basic_request_counts(self):
        self.create_request(status=ReturnRequest.Status.PENDING)
        self.create_request(status=ReturnRequest.Status.APPROVED)
        self.create_request(status=ReturnRequest.Status.DENIED)

        generate_daily_return_metrics()

        metrics = DailyReturnMetrics.objects.first()

        self.assertEqual(metrics.total_requests, 3)
        self.assertEqual(metrics.pending_requests, 1)
        self.assertEqual(metrics.approved_requests, 1)
        self.assertEqual(metrics.denied_requests, 1)

    def test_item_counts(self):
        req = self.create_request()

        self.create_item(req, status=ReturnRequestItem.Status.PENDING)
        self.create_item(req, status=ReturnRequestItem.Status.APPROVED)
        self.create_item(req, status=ReturnRequestItem.Status.DENIED)

        generate_daily_return_metrics()

        metrics = DailyReturnMetrics.objects.first()

        self.assertEqual(metrics.total_items, 3)
        self.assertEqual(metrics.pending_items, 1)
        self.assertEqual(metrics.approved_items, 1)
        self.assertEqual(metrics.denied_items, 1)

    def test_item_type_breakdown(self):
        req = self.create_request()

        self.create_item(req, item_type=ReturnRequestItem.ItemType.EQUIPMENT)
        self.create_item(req, item_type=ReturnRequestItem.ItemType.ACCESSORY)
        self.create_item(req, item_type=ReturnRequestItem.ItemType.CONSUMABLE)

        generate_daily_return_metrics()

        metrics = DailyReturnMetrics.objects.first()

        self.assertEqual(metrics.equipment_items, 1)
        self.assertEqual(metrics.accessory_items, 1)
        self.assertEqual(metrics.consumable_items, 1)

    # -------------------------
    # Time-based tests
    # -------------------------

    def test_requests_created_today(self):
        yesterday = self.now - timedelta(days=1)

        self.create_request(requested_at=yesterday)
        self.create_request(requested_at=self.now)

        generate_daily_return_metrics()

        metrics = DailyReturnMetrics.objects.first()

        self.assertEqual(metrics.requests_created_today, 1)

    def test_requests_processed_today(self):
        yesterday = self.now - timedelta(days=1)

        self.create_request(processed_at=yesterday)
        self.create_request(processed_at=self.now)

        generate_daily_return_metrics()

        metrics = DailyReturnMetrics.objects.first()

        self.assertEqual(metrics.requests_processed_today, 1)

    # -------------------------
    # Duration tests
    # -------------------------

    def test_processing_duration(self):
        req1 = self.create_request(
            requested_at=self.now - timedelta(hours=2),
            processed_at=self.now
        )

        req2 = self.create_request(
            requested_at=self.now - timedelta(hours=1),
            processed_at=self.now
        )

        generate_daily_return_metrics()

        metrics = DailyReturnMetrics.objects.first()

        self.assertGreater(metrics.avg_processing_time_seconds, 0)
        self.assertGreater(metrics.max_processing_time_seconds, 0)

    # -------------------------
    # Snapshot behavior
    # -------------------------

    def test_snapshot_created_once(self):
        generate_daily_return_metrics()
        generate_daily_return_metrics()

        self.assertEqual(DailyReturnMetrics.objects.count(), 1)

    
    def test_no_data(self):
        generate_daily_return_metrics()

        metrics = DailyReturnMetrics.objects.first()

        self.assertEqual(metrics.total_requests, 0)
        self.assertEqual(metrics.total_items, 0)
        self.assertEqual(metrics.avg_processing_time_seconds, 0)
        self.assertEqual(metrics.max_processing_time_seconds, 0)
    

    def test_no_processed_requests_duration_is_zero(self):
        self.create_request()  # no processed_at

        generate_daily_return_metrics()

        metrics = DailyReturnMetrics.objects.first()

        self.assertEqual(metrics.avg_processing_time_seconds, 0)
        self.assertEqual(metrics.max_processing_time_seconds, 0)



    def test_day_boundary_inclusion(self):
        start = timezone.make_aware(
            datetime.datetime.combine(self.today, datetime.datetime.min.time())
        )
        end = start + timedelta(days=1)

        # exactly at start → should count
        self.create_request(requested_at=start)

        # exactly at end → should NOT count
        self.create_request(requested_at=end)

        generate_daily_return_metrics()

        metrics = DailyReturnMetrics.objects.first()

        self.assertEqual(metrics.requests_created_today, 1)