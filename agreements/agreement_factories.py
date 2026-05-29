import factory

from agreements.models.agreements import AgreementCoverage, AgreementStatus, AgreementType, AssetAgreement, AssetAgreementItem, CoverageScopeType
from assets.asset_factories import EquipmentFactory
from sites.factories.site_factories import DepartmentFactory, LocationFactory, RoomFactory


class AgreementFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = AssetAgreement

    name = factory.Sequence(
        lambda n: f"Agreement {n}"
    )

    agreement_type = AgreementType.SERVICE
    status = AgreementStatus.ACTIVE
    vendor = factory.Faker("company")
    start_date = factory.Faker("date_object")

class AgreementCoverageFactory( factory.django.DjangoModelFactory ):

    class Meta:
        model = AgreementCoverage

    agreement = factory.SubFactory(
        AgreementFactory
    )
    scope_type = CoverageScopeType.GLOBAL

class GlobalCoverageFactory( factory.django.DjangoModelFactory ):

    class Meta:
        model = AgreementCoverage

    agreement = factory.SubFactory(
        AgreementFactory
    )

    scope_type = (
        CoverageScopeType.GLOBAL
    )

    department = None
    location = None
    room = None


class DepartmentCoverageFactory( AgreementCoverageFactory ):

    scope_type = CoverageScopeType.DEPARTMENT
    department = factory.SubFactory(
        DepartmentFactory
    )

class LocationCoverageFactory( AgreementCoverageFactory ):

    scope_type = CoverageScopeType.LOCATION
    location = factory.SubFactory(
        LocationFactory
    )

class RoomCoverageFactory( AgreementCoverageFactory ):

    scope_type = CoverageScopeType.ROOM

    room = factory.SubFactory(
        RoomFactory
    )

class AgreementItemFactory(
    factory.django.DjangoModelFactory
):

    class Meta:
        model = AssetAgreementItem

    agreement = factory.SubFactory(
        AgreementFactory
    )

    equipment = factory.SubFactory(
        EquipmentFactory
    )

    quantity = 1