from django.core.exceptions import ValidationError
from django.test import TestCase

from agreements.models.agreements import (
    AssetAgreementItem,
)

from agreements.services.coverage import (
    can_attach_asset_to_agreement,
)

from agreements.agreement_factories import AgreementFactory, RoomCoverageFactory
from assets.asset_factories import AccessoryFactory, ConsumableFactory, EquipmentFactory
from sites.factories.site_factories import (
    RoomFactory,
)


class AgreementAttachmentWorkflowTests(
    TestCase
):

    # =================================================
    # SUCCESSFUL ATTACHMENT
    # =================================================

    def test_equipment_can_be_attached_when_eligible(
        self,
    ):

        room = RoomFactory()

        equipment = EquipmentFactory(
            room=room,
        )

        agreement = AgreementFactory()

        RoomCoverageFactory(
            agreement=agreement,
            room=room,
        )

        eligible = can_attach_asset_to_agreement(
            agreement=agreement,
            asset=equipment,
        )

        self.assertTrue(
            eligible
        )

        item = AssetAgreementItem.objects.create(
            agreement=agreement,
            equipment=equipment,
        )

        self.assertEqual(
            item.equipment,
            equipment,
        )

        self.assertEqual(
            item.agreement,
            agreement,
        )

    def test_consumable_can_be_attached_when_eligible(
        self,
    ):

        room = RoomFactory()

        consumable = ConsumableFactory(
            room=room,
        )

        agreement = AgreementFactory()

        RoomCoverageFactory(
            agreement=agreement,
            room=room,
        )

        eligible = can_attach_asset_to_agreement(
            agreement=agreement,
            asset=consumable,
        )

        self.assertTrue(
            eligible
        )

        item = AssetAgreementItem.objects.create(
            agreement=agreement,
            consumable=consumable,
            quantity=10,
        )

        self.assertEqual(
            item.consumable,
            consumable,
        )

        self.assertEqual(
            item.quantity,
            10,
        )

    def test_accessory_can_be_attached_when_eligible(
        self,
    ):

        room = RoomFactory()

        accessory = AccessoryFactory(
            room=room,
        )

        agreement = AgreementFactory()

        RoomCoverageFactory(
            agreement=agreement,
            room=room,
        )

        eligible = can_attach_asset_to_agreement(
            agreement=agreement,
            asset=accessory,
        )

        self.assertTrue(
            eligible
        )

        item = AssetAgreementItem.objects.create(
            agreement=agreement,
            accessory=accessory,
            quantity=5,
        )

        self.assertEqual(
            item.accessory,
            accessory,
        )

    # =================================================
    # INVALID ATTACHMENT
    # =================================================

    def test_asset_cannot_attach_outside_coverage(
        self,
    ):

        covered_room = RoomFactory()

        other_room = RoomFactory()

        equipment = EquipmentFactory(
            room=other_room,
        )

        agreement = AgreementFactory()

        RoomCoverageFactory(
            agreement=agreement,
            room=covered_room,
        )

        eligible = can_attach_asset_to_agreement(
            agreement=agreement,
            asset=equipment,
        )

        self.assertFalse(
            eligible
        )

        with self.assertRaises(
            ValidationError
        ):

            item = AssetAgreementItem(
                agreement=agreement,
                equipment=equipment,
            )

            item.full_clean()

    # =================================================
    # DUPLICATE ATTACHMENT
    # =================================================

    def test_duplicate_equipment_attachment_is_rejected(
        self,
    ):

        room = RoomFactory()

        equipment = EquipmentFactory(
            room=room,
        )

        agreement = AgreementFactory()

        RoomCoverageFactory(
            agreement=agreement,
            room=room,
        )

        AssetAgreementItem.objects.create(
            agreement=agreement,
            equipment=equipment,
        )

        duplicate = AssetAgreementItem(
            agreement=agreement,
            equipment=equipment,
        )

        with self.assertRaises(
            ValidationError
        ):

            duplicate.full_clean()

    # =================================================
    # EQUIPMENT RULES
    # =================================================

    def test_equipment_quantity_is_forced_to_one(
        self,
    ):

        room = RoomFactory()

        equipment = EquipmentFactory(
            room=room,
        )

        agreement = AgreementFactory()

        RoomCoverageFactory(
            agreement=agreement,
            room=room,
        )

        item = AssetAgreementItem(
            agreement=agreement,
            equipment=equipment,
            quantity=2,
        )

        with self.assertRaises(
            ValidationError
        ):

            item.full_clean()

    # =================================================
    # SNAPSHOT INTEGRITY
    # =================================================

    def test_attachment_preserves_asset_snapshots(
        self,
    ):

        room = RoomFactory()

        equipment = EquipmentFactory(
            room=room,
            name="Latitude 7420",
            serial_number="DL-001",
        )

        agreement = AgreementFactory()

        RoomCoverageFactory(
            agreement=agreement,
            room=room,
        )

        item = AssetAgreementItem.objects.create(
            agreement=agreement,
            equipment=equipment,
        )

        equipment.name = "Renamed Device"

        equipment.save()

        item.refresh_from_db()

        self.assertEqual(
            item.asset_name_snapshot,
            "Latitude 7420",
        )

        self.assertEqual(
            item.asset_serial_snapshot,
            "DL-001",
        )

    # =================================================
    # ROOM RELOCATION REGRESSION
    # =================================================

    def test_asset_can_become_invalid_after_room_change(
        self,
    ):

        covered_room = RoomFactory()

        new_room = RoomFactory()

        equipment = EquipmentFactory(
            room=covered_room,
        )

        agreement = AgreementFactory()

        RoomCoverageFactory(
            agreement=agreement,
            room=covered_room,
        )

        item = AssetAgreementItem.objects.create(
            agreement=agreement,
            equipment=equipment,
        )

        self.assertTrue(
            item.is_asset_eligible()
        )

        equipment.room = new_room

        equipment.save()

        item.refresh_from_db()

        self.assertFalse(
            item.is_asset_eligible()
        )

    # =================================================
    # COVERAGE DATES
    # =================================================

    def test_attachment_with_valid_coverage_dates(
        self,
    ):

        room = RoomFactory()

        equipment = EquipmentFactory(
            room=room,
        )

        agreement = AgreementFactory()

        RoomCoverageFactory(
            agreement=agreement,
            room=room,
        )

        item = AssetAgreementItem.objects.create(
            agreement=agreement,
            equipment=equipment,
            coverage_start="2026-01-01",
            coverage_end="2026-12-31",
        )

        self.assertEqual(
            str(item.coverage_start),
            "2026-01-01",
        )

        self.assertEqual(
            str(item.coverage_end),
            "2026-12-31",
        )