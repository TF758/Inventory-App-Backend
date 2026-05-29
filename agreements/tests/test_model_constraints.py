from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase

from agreements.models.agreements import (
    AgreementCoverage,
    AssetAgreementItem,
    CoverageScopeType,
)

from agreements.agreement_factories import AgreementCoverageFactory, AgreementFactory, DepartmentCoverageFactory, LocationCoverageFactory, RoomCoverageFactory
from assets.asset_factories import AccessoryFactory, EquipmentFactory
from sites.factories.site_factories import (
    DepartmentFactory,
    LocationFactory,
    RoomFactory,
)


class AgreementCoverageConstraintTests(TestCase):

    # =================================================
    # GLOBAL COVERAGE
    # =================================================

    def test_global_coverage_cannot_coexist_with_scoped_coverage(
        self,
    ):

        department = DepartmentFactory()

        agreement = AgreementFactory()

        AgreementCoverageFactory(
            agreement=agreement,
            scope_type=CoverageScopeType.GLOBAL,
        )

        with self.assertRaises(
            ValidationError
        ):

            DepartmentCoverageFactory(
                agreement=agreement,
                department=department,
            )

    def test_scoped_coverage_cannot_coexist_with_global_coverage(
        self,
    ):

        department = DepartmentFactory()

        agreement = AgreementFactory()

        DepartmentCoverageFactory(
            agreement=agreement,
            department=department,
        )

        with self.assertRaises(
            ValidationError
        ):

            AgreementCoverageFactory(
                agreement=agreement,
                scope_type=CoverageScopeType.GLOBAL,
            )

    # =================================================
    # DUPLICATE SCOPE PREVENTION
    # =================================================

    def test_duplicate_department_coverage_blocked(
        self,
    ):

        department = DepartmentFactory()

        agreement = AgreementFactory()

        DepartmentCoverageFactory(
            agreement=agreement,
            department=department,
        )

        with self.assertRaises(
            ValidationError
        ):

            DepartmentCoverageFactory(
                agreement=agreement,
                department=department,
            )

    def test_duplicate_location_coverage_blocked(
        self,
    ):

        location = LocationFactory()

        agreement = AgreementFactory()

        LocationCoverageFactory(
            agreement=agreement,
            location=location,
        )

        with self.assertRaises(
            ValidationError
        ):

            LocationCoverageFactory(
                agreement=agreement,
                location=location,
            )

    def test_duplicate_room_coverage_blocked(
        self,
    ):

        room = RoomFactory()

        agreement = AgreementFactory()

        RoomCoverageFactory(
            agreement=agreement,
            room=room,
        )

        with self.assertRaises(
            ValidationError
        ):

            RoomCoverageFactory(
                agreement=agreement,
                room=room,
            )

    # =================================================
    # HIERARCHY REDUNDANCY
    # =================================================

    def test_department_coverage_blocks_redundant_location_coverage(
        self,
    ):

        department = DepartmentFactory()

        location = LocationFactory(
            department=department,
        )

        agreement = AgreementFactory()

        DepartmentCoverageFactory(
            agreement=agreement,
            department=department,
        )

        with self.assertRaises(
            ValidationError
        ):

            LocationCoverageFactory(
                agreement=agreement,
                location=location,
            )

    def test_department_coverage_blocks_redundant_room_coverage(
        self,
    ):

        department = DepartmentFactory()

        location = LocationFactory(
            department=department,
        )

        room = RoomFactory(
            location=location,
        )

        agreement = AgreementFactory()

        DepartmentCoverageFactory(
            agreement=agreement,
            department=department,
        )

        with self.assertRaises(
            ValidationError
        ):

            RoomCoverageFactory(
                agreement=agreement,
                room=room,
            )

    def test_location_coverage_blocks_redundant_room_coverage(
        self,
    ):

        location = LocationFactory()

        room = RoomFactory(
            location=location,
        )

        agreement = AgreementFactory()

        LocationCoverageFactory(
            agreement=agreement,
            location=location,
        )

        with self.assertRaises(
            ValidationError
        ):

            RoomCoverageFactory(
                agreement=agreement,
                room=room,
            )


class AssetAgreementItemConstraintTests(TestCase):

    # =================================================
    # EQUIPMENT QUANTITY
    # =================================================

    def test_equipment_quantity_must_be_one(
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
    # SINGLE ASSET ENFORCEMENT
    # =================================================

    def test_only_one_asset_type_may_be_attached(
        self,
    ):

        room = RoomFactory()

        equipment = EquipmentFactory(
            room=room,
        )

        accessory = AccessoryFactory(
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
            accessory=accessory,
        )

        with self.assertRaises(
            ValidationError
        ):

            item.full_clean()

    # =================================================
    # DUPLICATE ATTACHMENTS
    # =================================================

    def test_duplicate_equipment_attachment_blocked(
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
    # COVERAGE VALIDATION
    # =================================================

    def test_asset_outside_coverage_cannot_attach(
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

        item = AssetAgreementItem(
            agreement=agreement,
            equipment=equipment,
        )

        with self.assertRaises(
            ValidationError
        ):

            item.full_clean()

    # =================================================
    # COVERAGE DATE VALIDATION
    # =================================================

    def test_coverage_end_cannot_be_before_start(
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
            coverage_start="2026-01-10",
            coverage_end="2026-01-01",
        )

        with self.assertRaises(
            ValidationError
        ):

            item.full_clean()

    # =================================================
    # SNAPSHOT PRESERVATION
    # =================================================

    def test_asset_snapshots_are_captured_on_save(
        self,
    ):

        room = RoomFactory()

        equipment = EquipmentFactory(
            room=room,
            name="Dell Laptop",
            serial_number="ABC123",
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

        self.assertEqual(
            item.asset_name_snapshot,
            "Dell Laptop",
        )

        self.assertEqual(
            item.asset_serial_snapshot,
            "ABC123",
        )

        self.assertEqual(
            item.asset_public_id_snapshot,
            equipment.public_id,
        )