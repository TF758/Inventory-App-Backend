# agreements/tests/test_agreement_endpoints.py

from rest_framework import status
from rest_framework.test import APITestCase

from agreements.models.agreements import (
AssetAgreementItem,
)

from agreements.agreement_factories import AgreementFactory, DepartmentCoverageFactory, GlobalCoverageFactory, LocationCoverageFactory, RoomCoverageFactory
from assets.asset_factories import AccessoryFactory, ConsumableFactory, EquipmentFactory
from core.tests.authenticated_base import AuthenticatedAPITestCase
from users.factories.user_factories import AdminUserFactory
from sites.factories.site_factories import ( DepartmentFactory, LocationFactory, RoomFactory, )

class ApplicableAgreementEndpointTests( AuthenticatedAPITestCase ):

# =================================================
# REQUIRED PARAM
# =================================================

    def test_requires_asset_public_id(
        self,
    ):

        response = self.client.get(
            "/agreements/applicable/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertIn(
            "asset_public_id",
            response.data,
        )

    # =================================================
    # GLOBAL COVERAGE
    # =================================================

    def test_returns_global_agreements(
        self,
    ):

        equipment = EquipmentFactory()

        agreement = AgreementFactory()

        GlobalCoverageFactory(
            agreement=agreement,
        )

        response = self.client.get(
            "/agreements/applicable/",
            {
                "asset_public_id":
                equipment.public_id
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        results = response.data["results"]

        self.assertEqual(
            len(results),
            1,
        )

        self.assertEqual(
            results[0]["public_id"],
            agreement.public_id,
        )

    # =================================================
    # ROOM COVERAGE
    # =================================================

    def test_returns_room_coverage_agreements(
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

        response = self.client.get(
            "/agreements/applicable/",
            {
                "asset_public_id":
                equipment.public_id
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        results = response.data["results"]

        self.assertEqual(
            len(results),
            1,
        )

        self.assertEqual(
            results[0]["public_id"],
            agreement.public_id,
        )

    # =================================================
    # LOCATION COVERAGE
    # =================================================

    def test_returns_location_coverage_agreements(
        self,
    ):

        location = LocationFactory()

        room = RoomFactory(
            location=location,
        )

        equipment = EquipmentFactory(
            room=room,
        )

        agreement = AgreementFactory()

        LocationCoverageFactory(
            agreement=agreement,
            location=location,
        )

        response = self.client.get(
            "/agreements/applicable/",
            {
                "asset_public_id":
                equipment.public_id
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        results = response.data["results"]

        self.assertEqual(
            len(results),
            1,
        )

    # =================================================
    # DEPARTMENT COVERAGE
    # =================================================

    def test_returns_department_coverage_agreements(
        self,
    ):

        department = DepartmentFactory()

        location = LocationFactory(
            department=department,
        )

        room = RoomFactory(
            location=location,
        )

        equipment = EquipmentFactory(
            room=room,
        )

        agreement = AgreementFactory()

        DepartmentCoverageFactory(
            agreement=agreement,
            department=department,
        )

        response = self.client.get(
            "/agreements/applicable/",
            {
                "asset_public_id":
                equipment.public_id
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        results = response.data["results"]

        self.assertEqual(
            len(results),
            1,
        )

    # =================================================
    # EXCLUSION
    # =================================================

    def test_excludes_non_matching_agreements(
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

        response = self.client.get(
            "/agreements/applicable/",
            {
                "asset_public_id":
                equipment.public_id
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        results = response.data["results"]

        self.assertEqual(
            len(results),
            0,
        )

    # =================================================
    # PAGINATION
    # =================================================

    def test_applicable_endpoint_is_paginated(
        self,
    ):

        equipment = EquipmentFactory()

        for _ in range(25):

            agreement = AgreementFactory()

            GlobalCoverageFactory(
                agreement=agreement,
            )

        response = self.client.get(
            "/agreements/applicable/",
            {
                "asset_public_id":
                equipment.public_id,
                "page": 1,
                "page_size": 20,
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            len(response.data["results"]),
            20,
        )

        self.assertEqual(
            response.data["count"],
            25,
        )
  

class AgreementsByAssetEndpointTests( AuthenticatedAPITestCase ):
     


    # =================================================
    # REQUIRED PARAM
    # =================================================

    def test_requires_asset_public_id(
        self,
    ):

        response = self.client.get(
            "/agreements/by-asset/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertIn(
            "asset_public_id",
            response.data,
        )

    # =================================================
    # EQUIPMENT AGREEMENTS
    # =================================================

    def test_returns_attached_equipment_agreements(
        self,
    ):

        equipment = EquipmentFactory()

        agreement = AgreementFactory()

        GlobalCoverageFactory(
            agreement=agreement,
        )

        AssetAgreementItem.objects.create(
            agreement=agreement,
            equipment=equipment,
        )

        response = self.client.get(
            "/agreements/by-asset/",
            {
                "asset_public_id":
                equipment.public_id
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        results = response.data["results"]

        self.assertEqual(
            len(results),
            1,
        )

        self.assertEqual(
            results[0]["public_id"],
            agreement.public_id,
        )

    # =================================================
    # CONSUMABLE AGREEMENTS
    # =================================================

    def test_returns_attached_consumable_agreements(
        self,
    ):

        consumable = ConsumableFactory()

        agreement = AgreementFactory()

        GlobalCoverageFactory(
            agreement=agreement,
        )

        AssetAgreementItem.objects.create(
            agreement=agreement,
            consumable=consumable,
            quantity=5,
        )

        response = self.client.get(
            "/agreements/by-asset/",
            {
                "asset_public_id":
                consumable.public_id
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        results = response.data["results"]

        self.assertEqual(
            len(results),
            1,
        )

    # =================================================
    # ACCESSORY AGREEMENTS
    # =================================================

    def test_returns_attached_accessory_agreements(
        self,
    ):

        accessory = AccessoryFactory()

        agreement = AgreementFactory()

        GlobalCoverageFactory(
            agreement=agreement,
        )

        AssetAgreementItem.objects.create(
            agreement=agreement,
            accessory=accessory,
            quantity=2,
        )

        response = self.client.get(
            "/agreements/by-asset/",
            {
                "asset_public_id":
                accessory.public_id
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        results = response.data["results"]

        self.assertEqual(
            len(results),
            1,
        )

    # =================================================
    # ONLY ATTACHED AGREEMENTS
    # =================================================

    def test_excludes_merely_applicable_agreements(
        self,
    ):

        equipment = EquipmentFactory()

        attached_agreement = AgreementFactory()

        applicable_only = AgreementFactory()

        GlobalCoverageFactory(
            agreement=attached_agreement,
        )

        GlobalCoverageFactory(
            agreement=applicable_only,
        )

        AssetAgreementItem.objects.create(
            agreement=attached_agreement,
            equipment=equipment,
        )

        response = self.client.get(
            "/agreements/by-asset/",
            {
                "asset_public_id":
                equipment.public_id
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        results = response.data["results"]

        self.assertEqual(
            len(results),
            1,
        )

        self.assertEqual(
            results[0]["public_id"],
            attached_agreement.public_id,
        )

    # =================================================
    # EMPTY RESULTS
    # =================================================

    def test_returns_empty_when_asset_has_no_agreements(
        self,
    ):

        equipment = EquipmentFactory()

        response = self.client.get(
            "/agreements/by-asset/",
            {
                "asset_public_id":
                equipment.public_id
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            len(response.data["results"]),
            0,
        )

    # =================================================
    # PAGINATION
    # =================================================

    def test_by_asset_endpoint_is_paginated(
        self,
    ):

        equipment = EquipmentFactory()

        for _ in range(25):

            agreement = AgreementFactory()

            GlobalCoverageFactory(
                agreement=agreement,
            )

            AssetAgreementItem.objects.create(
                agreement=agreement,
                equipment=equipment,
            )

        response = self.client.get(
            "/agreements/by-asset/",
            {
                "asset_public_id":
                equipment.public_id,
                "page": 1,
                "page_size": 20,
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            len(response.data["results"]),
            20,
        )

        self.assertEqual(
            response.data["count"],
            25,
        )
