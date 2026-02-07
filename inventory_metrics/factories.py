import factory
from factory import fuzzy
from django.utils import timezone
import random
from db_inventory.models import Department, Location
from db_inventory.factories import DepartmentFactory
from inventory_metrics.models.metrics import DailyAuthMetrics
from inventory_metrics.models import (
    DailySystemMetrics,
    DailySecurityMetrics,
    DailyRoleMetrics,
    DailyDepartmentSnapshot,
    DailyLocationSnapshot,
    DailyLoginMetrics
)

# --------------------------
# Daily System Metrics
# --------------------------
class DailySystemMetricsFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = DailySystemMetrics

    date = factory.LazyFunction(lambda: timezone.localdate())

    # User metrics
    total_users = fuzzy.FuzzyInteger(5_000, 15_000)
    active_users_last_24h = fuzzy.FuzzyInteger(1_000, 5_000)
    active_users_last_7d = fuzzy.FuzzyInteger(2_000, 10_000)
    new_users_last_24h = fuzzy.FuzzyInteger(10, 200)
    locked_users = fuzzy.FuzzyInteger(0, 50)

    # Session metrics
    total_sessions = fuzzy.FuzzyInteger(10_000, 50_000)
    active_sessions = fuzzy.FuzzyInteger(5_000, 25_000)
    revoked_sessions = fuzzy.FuzzyInteger(0, 1_000)
    expired_sessions_last_24h = fuzzy.FuzzyInteger(0, 500)
    unique_users_logged_in_last_24h = fuzzy.FuzzyInteger(800, 4_000)

    # Inventory metrics
    total_equipment = fuzzy.FuzzyInteger(1_000, 5_000)
    equipment_ok = fuzzy.FuzzyInteger(700, 4_000)
    equipment_under_repair = fuzzy.FuzzyInteger(0, 500)
    equipment_damaged = fuzzy.FuzzyInteger(0, 300)

    total_components = fuzzy.FuzzyInteger(2_000, 10_000)
    total_components_quantity = fuzzy.FuzzyInteger(5_000, 20_000)
    total_consumables = fuzzy.FuzzyInteger(500, 2_000)
    total_consumables_quantity = fuzzy.FuzzyInteger(1_000, 5_000)
    total_accessories = fuzzy.FuzzyInteger(300, 1_500)
    total_accessories_quantity = fuzzy.FuzzyInteger(1_000, 4_000)

    schema_version = 1

# --------------------------
# Daily Auth Metrics
# --------------------------
class DailyAuthMetricsFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = DailyAuthMetrics

    date = factory.LazyFunction(lambda: timezone.localdate())

    # Login events
    total_logins = fuzzy.FuzzyInteger(50, 500)
    unique_users_logged_in = fuzzy.FuzzyInteger(20, 300)
    failed_logins = fuzzy.FuzzyInteger(0, 100)
    lockouts = fuzzy.FuzzyInteger(0, 20)

    # Sessions
    active_sessions = fuzzy.FuzzyInteger(100, 5_000)
    revoked_sessions = fuzzy.FuzzyInteger(0, 500)
    expired_sessions = fuzzy.FuzzyInteger(0, 500)
    users_multiple_active_sessions = fuzzy.FuzzyInteger(0, 200)
    users_with_revoked_sessions = fuzzy.FuzzyInteger(0, 100)

    # Password resets
    password_resets_started = fuzzy.FuzzyInteger(0, 100)
    password_resets_completed = fuzzy.FuzzyInteger(0, 80)
    active_password_resets = fuzzy.FuzzyInteger(0, 50)
    expired_password_resets = fuzzy.FuzzyInteger(0, 30)

    schema_version = 1

# --------------------------
class DailyDepartmentSnapshotFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = DailyDepartmentSnapshot

    department = factory.SubFactory(DepartmentFactory)
    snapshot_date = factory.LazyFunction(lambda: timezone.localdate())

    schema_version = 1
    created_by = "test_factory"

    total_users = fuzzy.FuzzyInteger(0, 1_000)
    total_admins = fuzzy.FuzzyInteger(0, 50)

    total_locations = fuzzy.FuzzyInteger(1, 20)
    total_rooms = fuzzy.FuzzyInteger(5, 100)

    total_equipment = fuzzy.FuzzyInteger(10, 500)
    equipment_ok = fuzzy.FuzzyInteger(5, 400)
    equipment_under_repair = fuzzy.FuzzyInteger(0, 50)
    equipment_damaged = fuzzy.FuzzyInteger(0, 30)

    total_components = fuzzy.FuzzyInteger(20, 1_000)
    total_components_quantity = fuzzy.FuzzyInteger(50, 5_000)

    total_consumables = fuzzy.FuzzyInteger(5, 200)
    total_consumables_quantity = fuzzy.FuzzyInteger(10, 1_000)

    total_accessories = fuzzy.FuzzyInteger(5, 200)
    total_accessories_quantity = fuzzy.FuzzyInteger(10, 1_000)