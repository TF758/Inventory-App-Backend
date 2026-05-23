from datetime import timedelta

import factory

from django.utils import timezone

from agreements.models.agreements import (
    AssetAgreement,
    AssetAgreementItem,
    AgreementCoverage,
    AgreementType,
    CoverageScopeType,
)
from assets.asset_factories import AccessoryFactory, ConsumableFactory, EquipmentFactory
from sites.factories.site_factories import DepartmentFactory, LocationFactory, RoomFactory





# -----------------------------------------------------
# Agreement
# -----------------------------------------------------


class AssetAgreementFactory(
    factory.django.DjangoModelFactory
):

    class Meta:
        model = AssetAgreement

    name = factory.Sequence(
        lambda n: f"Agreement {n}"
    )

    agreement_type = (
        AgreementType.SERVICE
    )

    status = "ACTIVE"

    vendor = factory.Faker("company")

    reference_number = factory.Sequence(
        lambda n: f"AGR-{n:05d}"
    )

    start_date = factory.LazyFunction(
        lambda: timezone.now().date()
    )

    expiry_date = factory.LazyFunction(
        lambda: (
            timezone.now().date()
            + timedelta(days=365)
        )
    )

    renewal_date = factory.LazyAttribute(
        lambda obj: (
            obj.expiry_date - timedelta(days=30)
        )
    )

    auto_renew = False

    currency = "USD"

    cost = factory.Faker(
        "pydecimal",
        left_digits=4,
        right_digits=2,
        positive=True,
    )

    managing_department = factory.SubFactory(
        DepartmentFactory
    )


# -----------------------------------------------------
# Agreement Coverage
# -----------------------------------------------------


class AgreementCoverageFactory(
    factory.django.DjangoModelFactory
):

    class Meta:
        model = AgreementCoverage

    agreement = factory.SubFactory(
        AssetAgreementFactory
    )

    scope_type = (
        CoverageScopeType.GLOBAL
    )

    notes = factory.Faker("sentence")


class DepartmentAgreementCoverageFactory(
    AgreementCoverageFactory
):

    scope_type = (
        CoverageScopeType.DEPARTMENT
    )

    department = factory.SubFactory(
        DepartmentFactory
    )


class LocationAgreementCoverageFactory(
    AgreementCoverageFactory
):

    scope_type = (
        CoverageScopeType.LOCATION
    )

    location = factory.SubFactory(
        LocationFactory
    )


class RoomAgreementCoverageFactory(
    AgreementCoverageFactory
):

    scope_type = (
        CoverageScopeType.ROOM
    )

    room = factory.SubFactory(
        RoomFactory
    )


# -----------------------------------------------------
# Agreement Item
# -----------------------------------------------------


class AssetAgreementItemFactory(
    factory.django.DjangoModelFactory
):

    class Meta:
        model = AssetAgreementItem

    agreement = factory.SubFactory(
        AssetAgreementFactory
    )

    equipment = factory.SubFactory(
        EquipmentFactory
    )

    consumable = None

    accessory = None

    quantity = 1

    coverage_start = factory.LazyFunction(
        lambda: timezone.now().date()
    )

    coverage_end = factory.LazyFunction(
        lambda: (
            timezone.now().date()
            + timedelta(days=365)
        )
    )

    @factory.post_generation
    def ensure_coverage(
        obj,
        create,
        extracted,
        **kwargs,
    ):

        """
        Ensure agreement coverage exists
        for the asset room hierarchy.
        """

        if not create:
            return

        asset = obj.asset

        if not asset:
            return

        room = getattr(asset, "room", None)

        if not room:
            return

        AgreementCoverage.objects.get_or_create(
            agreement=obj.agreement,
            scope_type=CoverageScopeType.ROOM,
            room=room,
        )

    class Params:

        consumable_asset = factory.Trait(

            equipment=None,

            consumable=factory.SubFactory(
                ConsumableFactory
            ),

            accessory=None,

            quantity=5,
        )

        accessory_asset = factory.Trait(

            equipment=None,

            consumable=None,

            accessory=factory.SubFactory(
                AccessoryFactory
            ),
        )