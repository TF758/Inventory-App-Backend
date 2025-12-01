import factory
from factory import fuzzy
from django.utils import timezone
import random
from db_inventory.models import Department, Location
from inventory_metrics.models import (
    DailySystemMetrics,
    DailySecurityMetrics,
    DailyRoleMetrics,
    DailyDepartmentSnapshot,
    DailyLocationSnapshot,
)

# --------------------------
# Daily System Metrics
# --------------------------
class DailySystemMetricsFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = DailySystemMetrics

    date = factory.LazyFunction(lambda: timezone.now().date())
    total_users = fuzzy.FuzzyInteger(5000, 15000)
    active_users_last_24h = fuzzy.FuzzyInteger(1000, 5000)
    active_users_last_7d = fuzzy.FuzzyInteger(2000, 10000)
    new_users_last_24h = fuzzy.FuzzyInteger(10, 200)
    locked_users = fuzzy.FuzzyInteger(0, 50)
    total_sessions = fuzzy.FuzzyInteger(10000, 50000)
    active_sessions = fuzzy.FuzzyInteger(5000, 25000)
    revoked_sessions = fuzzy.FuzzyInteger(0, 1000)
    expired_sessions_last_24h = fuzzy.FuzzyInteger(0, 500)
    unique_users_logged_in_last_24h = fuzzy.FuzzyInteger(800, 4000)
    total_equipment = fuzzy.FuzzyInteger(1000, 5000)
    total_components = fuzzy.FuzzyInteger(2000, 10000)
    total_components_quantity = fuzzy.FuzzyInteger(5000, 20000)
    total_consumables = fuzzy.FuzzyInteger(500, 2000)
    total_consumables_quantity = fuzzy.FuzzyInteger(1000, 5000)
    total_accessories = fuzzy.FuzzyInteger(300, 1500)
    total_accessories_quantity = fuzzy.FuzzyInteger(1000, 4000)

# --------------------------
# Daily Security Metrics
# --------------------------
class DailySecurityMetricsFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = DailySecurityMetrics

    date = factory.LazyFunction(lambda: timezone.now().date())
    password_resets = fuzzy.FuzzyInteger(0, 200)
    active_password_resets = fuzzy.FuzzyInteger(0, 50)
    expired_password_resets = fuzzy.FuzzyInteger(0, 20)
    users_multiple_active_sessions = fuzzy.FuzzyInteger(0, 100)
    users_with_revoked_sessions = fuzzy.FuzzyInteger(0, 50)

# --------------------------
# Daily Role Metrics
# --------------------------
class DailyRoleMetricsFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = DailyRoleMetrics

    date = factory.LazyFunction(lambda: timezone.now().date())
    role = factory.LazyFunction(lambda: random.choice([
        "ROOM_VIEWER", "ROOM_CLERK", "ROOM_ADMIN",
        "LOCATION_VIEWER", "LOCATION_ADMIN",
        "DEPARTMENT_VIEWER", "DEPARTMENT_ADMIN",
        "SITE_ADMIN"
    ]))
    total_users_with_role = fuzzy.FuzzyInteger(0, 5000)
    total_users_active_with_role = fuzzy.FuzzyInteger(0, 5000)

# --------------------------
# Daily Department Snapshot
# --------------------------
class DailyDepartmentSnapshotFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = DailyDepartmentSnapshot

    department = factory.LazyFunction(lambda: random.choice(Department.objects.all()))
    snapshot_date = factory.LazyFunction(lambda: timezone.now().date())
    total_users = fuzzy.FuzzyInteger(0, 1000)
    total_admins = fuzzy.FuzzyInteger(0, 50)
    total_locations = fuzzy.FuzzyInteger(1, 20)
    total_rooms = fuzzy.FuzzyInteger(5, 100)
    total_equipment = fuzzy.FuzzyInteger(10, 500)
    total_components = fuzzy.FuzzyInteger(20, 1000)
    total_component_quantity = fuzzy.FuzzyInteger(50, 5000)
    total_consumables = fuzzy.FuzzyInteger(5, 200)
    total_consumables_quantity = fuzzy.FuzzyInteger(10, 1000)
    total_accessories = fuzzy.FuzzyInteger(5, 200)
    total_accessories_quantity = fuzzy.FuzzyInteger(10, 1000)

# --------------------------
# Daily Location Snapshot
# --------------------------
class DailyLocationSnapshotFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = DailyLocationSnapshot

    location = factory.LazyFunction(lambda: random.choice(Location.objects.all()))
    snapshot_date = factory.LazyFunction(lambda: timezone.now().date())
    total_users = fuzzy.FuzzyInteger(0, 500)
    total_admins = fuzzy.FuzzyInteger(0, 20)
    total_rooms = fuzzy.FuzzyInteger(1, 50)
    total_equipment = fuzzy.FuzzyInteger(5, 200)
    total_components = fuzzy.FuzzyInteger(10, 500)
    total_component_quantity = fuzzy.FuzzyInteger(20, 2000)
    total_consumables = fuzzy.FuzzyInteger(5, 100)
    total_consumables_quantity = fuzzy.FuzzyInteger(10, 500)
    total_accessories = fuzzy.FuzzyInteger(5, 100)
    total_accessories_quantity = fuzzy.FuzzyInteger(10, 500)
