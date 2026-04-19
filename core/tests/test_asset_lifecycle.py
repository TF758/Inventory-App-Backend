from django.test import TestCase
from django.utils import timezone
from unittest.mock import patch
from core.models.audit import AuditLog
from assignments.services.equipment_assignment import StatusChangeResult
from assets.asset_factories import AccessoryFactory, ConsumableFactory, EquipmentFactory
from assets.services.assets import hard_delete_asset, restore_asset, soft_delete_asset
from users.factories.user_factories import AdminUserFactory



class _BaseAssetLifecycleTest():

    __test__ = False
    asset_factory = None

    def setUp(self):

        # --- Patch permissions ---
        self.soft_patch = patch(
            "assets.services.assets.can_soft_delete_asset",
            return_value=True,
        )
        self.hard_patch = patch(
            "assets.services.assets.can_hard_delete_asset",
            return_value=True,
        )

        self.soft_patch.start()
        self.hard_patch.start()

        self.addCleanup(self.soft_patch.stop)
        self.addCleanup(self.hard_patch.stop)

        self.admin = AdminUserFactory()
        self.asset = self.asset_factory()

    # -----------------------------
    # SOFT DELETE
    # -----------------------------
    def test_soft_delete_success(self):
        result = soft_delete_asset(
            actor=self.admin,
            asset=self.asset,
            batch=False,
            use_atomic=False,
            lock_asset=False,
        )

        self.asset.refresh_from_db()

        self.assertEqual(result, StatusChangeResult.SUCCESS)
        self.assertTrue(self.asset.is_deleted)
        self.assertIsNotNone(self.asset.deleted_at)

        self.assertTrue(
            AuditLog.objects.filter(target_id=self.asset.public_id).exists()
        )

    # -----------------------------
    # RESTORE
    # -----------------------------
    def test_restore_success(self):
        self.asset.is_deleted = True
        self.asset.deleted_at = timezone.now()
        self.asset.save()

        result = restore_asset(
            actor=self.admin,
            asset=self.asset,
            batch=False,
            use_atomic=False,
            lock_asset=False,
        )

        self.asset.refresh_from_db()

        self.assertEqual(result, StatusChangeResult.SUCCESS)
        self.assertFalse(self.asset.is_deleted)
        self.assertIsNone(self.asset.deleted_at)

    # -----------------------------
    # HARD DELETE
    # -----------------------------
    def test_hard_delete_success(self):
        pk = self.asset.pk

        result = hard_delete_asset(
            actor=self.admin,
            asset=self.asset,
            batch=False,
            use_atomic=False,
            lock_asset=False,
        )

        self.assertEqual(result, StatusChangeResult.SUCCESS)
        self.assertFalse(type(self.asset).objects.filter(pk=pk).exists())

    def test_soft_delete_skipped_if_already_deleted(self):
        self.asset.is_deleted = True
        self.asset.save()

        result = soft_delete_asset(
            actor=self.admin,
            asset=self.asset,
            use_atomic=False,
            lock_asset=False,
        )

        self.assertEqual(result, StatusChangeResult.SKIPPED)


class EquipmentLifecycleTests(_BaseAssetLifecycleTest, TestCase):
    asset_factory = EquipmentFactory


class AccessoryLifecycleTests(_BaseAssetLifecycleTest, TestCase):
    asset_factory = AccessoryFactory


class ConsumableLifecycleTests(_BaseAssetLifecycleTest, TestCase):
    asset_factory = ConsumableFactory