import datetime
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from analytics.models.metrics import DailySystemMetrics
from analytics.services.snapshots import generate_daily_system_metrics
from assets.asset_factories import AccessoryFactory, ComponentFactory, ConsumableFactory, EquipmentFactory
from core.factories.audit_factories import AuditLogFactory
from core.factories.session_factories import UserSessionFactory
from core.models.audit import AuditLog
from core.models.sessions import UserSession
from assets.models.assets import Accessory, Consumable
from sites.factories.site_factories import RoomFactory
from users.factories.user_factories import User, UserFactory



class TestDailySystemMetrics(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.now = timezone.now()
        cls.today = timezone.localdate()
        cls.room = RoomFactory()

    # -------------------------
    # Helpers
    # -------------------------

    def run_snapshot(self):
        generate_daily_system_metrics()
        return DailySystemMetrics.objects.first()

    def create_user(self, **kwargs):
        user = UserFactory(**kwargs)

        if "last_login" in kwargs or "date_joined" in kwargs:
            User.objects.filter(pk=user.pk).update(
                last_login=kwargs.get("last_login", user.last_login),
                date_joined=kwargs.get("date_joined", user.date_joined),
            )

        return user

    def create_session(self, user, created_at, expires_at, status, last_used_at=None):
        session = UserSessionFactory(
            user=user,
            status=status,
            expires_at=expires_at,
            absolute_expires_at=expires_at,
        )

        UserSession.objects.filter(pk=session.pk).update(
            created_at=created_at,
            last_used_at=last_used_at,
        )

        return session

    def create_audit(self, event_type, created_at, user=None):
        obj = AuditLogFactory.build(
            event_type=event_type,
            created_at=created_at,
            user=user,
        )

        data = {
            field.name: getattr(obj, field.name)
            for field in AuditLog._meta.fields
        }

        return AuditLog.objects.create(**data)

    # -------------------------
    # 1. Baseline (empty system)
    # -------------------------

    def test_empty_system(self):
        metrics = self.run_snapshot()

        self.assertEqual(metrics.total_users, 0)
        self.assertEqual(metrics.total_sessions, 0)
        self.assertEqual(metrics.total_equipment, 0)

    # -------------------------
    # 2. User metrics
    # -------------------------

    def test_user_counts(self):
        UserFactory(is_system_user=True)
        UserFactory(is_system_user=False)

        metrics = self.run_snapshot()

        self.assertEqual(metrics.total_users, 2)
        self.assertEqual(metrics.system_users, 1)
        self.assertEqual(metrics.human_users, 1)

    def test_active_users_today_boundary(self):
        start = timezone.make_aware(
            datetime.datetime.combine(self.today, datetime.datetime.min.time())
        )
        end = start + timedelta(days=1)

        self.create_user(last_login=start)  # included
        self.create_user(last_login=end)    # excluded

        metrics = self.run_snapshot()

        self.assertEqual(metrics.active_users_today, 1)

    # -------------------------
    # 3. Session metrics
    # -------------------------

    def test_active_sessions_overlap_logic(self):
        start = timezone.make_aware(
            datetime.datetime.combine(self.today, datetime.datetime.min.time())
        )
        end = start + timedelta(days=1)

        user = UserFactory()

        # overlaps → should count
        self.create_session(
            user=user,
            created_at=start,
            expires_at=end,
            status=UserSession.Status.ACTIVE,
        )

        # outside window → should NOT count
        self.create_session(
            user=user,
            created_at=end,
            expires_at=end + timedelta(hours=1),
            status=UserSession.Status.ACTIVE,
        )

        metrics = self.run_snapshot()
        self.assertEqual(metrics.active_sessions, 1)

    def test_unique_users_logged_in_deduplicated(self):
        user = UserFactory()

        self.create_session(
            user=user,
            created_at=self.now,
            expires_at=self.now + timedelta(hours=1),
            status=UserSession.Status.ACTIVE,
            last_used_at=self.now,
        )

        self.create_session(
            user=user,
            created_at=self.now,
            expires_at=self.now + timedelta(hours=1),
            status=UserSession.Status.ACTIVE,
            last_used_at=self.now,
        )

        metrics = self.run_snapshot()
        self.assertEqual(metrics.unique_users_logged_in_today, 1)

    def test_revoked_sessions_event_based(self):
        user = UserFactory()

        self.create_audit(AuditLog.Events.SESSION_REVOKED, self.now, user)
        self.create_audit(AuditLog.Events.SESSION_REVOKED, self.now, user)

        metrics = self.run_snapshot()

        self.assertEqual(metrics.revoked_sessions_today, 2)

    # -------------------------
    # 4. Inventory metrics
    # -------------------------

    def test_inventory_quantities(self):
        EquipmentFactory()

        Accessory.objects.create(name="A", quantity=3, room=self.room)
        Consumable.objects.create(name="C", quantity=7, room=self.room)

        metrics = self.run_snapshot()

        self.assertEqual(metrics.total_equipment, 1)
        self.assertEqual(metrics.total_accessories_quantity, 3)
        self.assertEqual(metrics.total_consumables_quantity, 7)

    def test_deleted_equipment_excluded(self):
        EquipmentFactory(is_deleted=True)
        EquipmentFactory(is_deleted=False)

        metrics = self.run_snapshot()
        self.assertEqual(metrics.total_equipment, 1)

    # -------------------------
    # 5. Idempotency (CRITICAL)
    # -------------------------

    def test_snapshot_created_once(self):
        generate_daily_system_metrics()
        generate_daily_system_metrics()

        self.assertEqual(DailySystemMetrics.objects.count(), 1)