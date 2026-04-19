import factory
from django.utils import timezone
from datetime import timedelta
from assets.models.assets import AssetAgreement, AssetAgreementItem
from assets.asset_factories import AccessoryFactory, ConsumableFactory, EquipmentFactory
from sites.factories.site_factories import DepartmentFactory


class AssetAgreementFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AssetAgreement

    name = factory.Sequence(lambda n: f"Agreement {n}")
    agreement_type = AssetAgreement.AgreementType.CONTRACT
    vendor = factory.Faker("company")
    reference_number = factory.Sequence(lambda n: f"AGR-{n:05d}")

    start_date = factory.LazyFunction(lambda: timezone.now().date())
    expiry_date = factory.LazyFunction(lambda: timezone.now().date() + timedelta(days=365))

    cost = factory.Faker("pydecimal", left_digits=4, right_digits=2, positive=True)

    department = factory.SubFactory(DepartmentFactory)


class AssetAgreementItemFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AssetAgreementItem

    agreement = factory.SubFactory(AssetAgreementFactory)
    equipment = factory.SubFactory(EquipmentFactory)

    consumable = None
    accessory = None
    quantity = 1

    class Params:
        consumable_asset = factory.Trait(
            equipment=None,
            consumable=factory.SubFactory(ConsumableFactory),
            accessory=None,
        )

        accessory_asset = factory.Trait(
            equipment=None,
            consumable=None,
            accessory=factory.SubFactory(AccessoryFactory),
        )