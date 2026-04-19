import factory
from django.utils import timezone
from core.models.audit import AuditLog, SiteNameChangeHistory, SiteRelocationHistory

class AuditLogFactory(factory.Factory):
    """
    Build-only factory for AuditLog.
    Safe for bulk_create (no save(), no side effects).
    """

    class Meta:
        model = AuditLog

    # Actor
    user = None
    user_public_id = None
    user_email = factory.Faker("email")

    # Event
    event_type = AuditLog.Events.LOGIN
    description = "User logged in"
    metadata = factory.LazyFunction(dict)

    # Target snapshots
    target_model = None
    target_id = None
    target_name = None

    # Org snapshots
    department = None
    department_name = None
    location = None
    location_name = None
    room = None
    room_name = None

    # Request context
    ip_address = factory.Faker("ipv4")
    user_agent = factory.Faker("user_agent")

    created_at = factory.LazyFunction(timezone.now)




class SiteNameChangeHistoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SiteNameChangeHistory

    site_type = SiteNameChangeHistory.SiteType.DEPARTMENT
    object_public_id = factory.Sequence(lambda n: f"SITE-{n:05d}")
    old_name = factory.Faker("company")
    new_name = factory.Faker("company")
    user = factory.SubFactory("core.factories.user.UserFactory")
    user_email = factory.LazyAttribute(lambda o: o.user.email if o.user else None)
    reason = factory.Faker("sentence", nb_words=6)

class SiteRelocationHistoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SiteRelocationHistory

    site_type = SiteRelocationHistory.SiteType.LOCATION

    object_public_id = factory.Sequence(lambda n: f"SITE-{n:05d}")
    object_name = factory.Faker("company")

    from_parent_public_id = factory.Sequence(lambda n: f"PAR-{n:05d}")
    from_parent_name = factory.Faker("company")

    to_parent_public_id = factory.Sequence(lambda n: f"PAR-{n:05d}")
    to_parent_name = factory.Faker("company")

    user = factory.SubFactory("core.factories.user.UserFactory")
    user_email = factory.LazyAttribute(lambda o: o.user.email if o.user else None)

    reason = factory.Faker("sentence", nb_words=8)