from django.test import TestCase
from agreements.models.agreements import ( CoverageScopeType, )
from agreements.services.coverage import ( agreement_covers_room, can_attach_asset_to_agreement, )
from agreements.agreement_factories import AgreementFactory, DepartmentCoverageFactory, LocationCoverageFactory, RoomCoverageFactory
from assets.asset_factories import EquipmentFactory
from core.factories.agreement_factories import AgreementCoverageFactory
from sites.factories.site_factories import ( DepartmentFactory, LocationFactory, RoomFactory, )


class AgreementCoverageServiceTests(TestCase):

    # =================================================
    # GLOBAL COVERAGE
    # =================================================

    def test_global_coverage_matches_any_room(
        self,
    ):

        room = RoomFactory()

        agreement = AgreementFactory()

        AgreementCoverageFactory(
            agreement=agreement,
            scope_type=CoverageScopeType.GLOBAL,
        )

        result = agreement_covers_room(
            agreement=agreement,
            room=room,
        )

        self.assertTrue(result)

    # =================================================
    # ROOM COVERAGE
    # =================================================

    def test_room_coverage_matches_exact_room(
        self,
    ):

        room = RoomFactory()

        agreement = AgreementFactory()

        RoomCoverageFactory(
            agreement=agreement,
            room=room,
        )

        result = agreement_covers_room(
            agreement=agreement,
            room=room,
        )

        self.assertTrue(result)

    def test_room_coverage_rejects_other_rooms(
        self,
    ):

        covered_room = RoomFactory()

        other_room = RoomFactory()

        agreement = AgreementFactory()

        RoomCoverageFactory(
            agreement=agreement,
            room=covered_room,
        )

        result = agreement_covers_room(
            agreement=agreement,
            room=other_room,
        )

        self.assertFalse(result)

    # =================================================
    # LOCATION COVERAGE
    # =================================================

    def test_location_coverage_matches_rooms_within_location(
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

        result = agreement_covers_room(
            agreement=agreement,
            room=room,
        )

        self.assertTrue(result)

    def test_location_coverage_rejects_other_locations(
        self,
    ):

        covered_location = LocationFactory()

        other_location = LocationFactory()

        other_room = RoomFactory(
            location=other_location,
        )

        agreement = AgreementFactory()

        LocationCoverageFactory(
            agreement=agreement,
            location=covered_location,
        )

        result = agreement_covers_room(
            agreement=agreement,
            room=other_room,
        )

        self.assertFalse(result)

    # =================================================
    # DEPARTMENT COVERAGE
    # =================================================

    def test_department_coverage_matches_rooms_within_department(
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

        result = agreement_covers_room(
            agreement=agreement,
            room=room,
        )

        self.assertTrue(result)

    def test_department_coverage_rejects_other_departments(
        self,
    ):

        covered_department = DepartmentFactory()

        other_department = DepartmentFactory()

        covered_location = LocationFactory(
            department=covered_department,
        )

        other_location = LocationFactory(
            department=other_department,
        )

        other_room = RoomFactory(
            location=other_location,
        )

        agreement = AgreementFactory()

        DepartmentCoverageFactory(
            agreement=agreement,
            department=covered_department,
        )

        result = agreement_covers_room(
            agreement=agreement,
            room=other_room,
        )

        self.assertFalse(result)

    # =================================================
    # ASSET ELIGIBILITY
    # =================================================

    def test_asset_can_attach_when_room_is_covered(
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

        result = can_attach_asset_to_agreement(
            agreement=agreement,
            asset=equipment,
        )

        self.assertTrue(result)

    def test_asset_cannot_attach_when_room_not_covered(
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

        result = can_attach_asset_to_agreement(
            agreement=agreement,
            asset=equipment,
        )

        self.assertFalse(result)

    def test_asset_without_room_cannot_attach(
        self,
    ):

        equipment = EquipmentFactory(
            room=None,
        )

        agreement = AgreementFactory()

        AgreementCoverageFactory(
            agreement=agreement,
            scope_type=CoverageScopeType.GLOBAL,
        )

        result = can_attach_asset_to_agreement(
            agreement=agreement,
            asset=equipment,
        )

        self.assertFalse(result)

    # =================================================
    # EDGE CASES
    # =================================================

    def test_agreement_without_coverages_rejects_room(
        self,
    ):

        room = RoomFactory()

        agreement = AgreementFactory()

        result = agreement_covers_room(
            agreement=agreement,
            room=room,
        )

        self.assertFalse(result)

    def test_none_room_returns_false(
        self,
    ):

        agreement = AgreementFactory()

        AgreementCoverageFactory(
            agreement=agreement,
            scope_type=CoverageScopeType.GLOBAL,
        )

        result = agreement_covers_room(
            agreement=agreement,
            room=None,
        )

        self.assertFalse(result)