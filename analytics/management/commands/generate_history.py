import datetime
import random
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction, models
from tqdm import tqdm
from db_inventory.models.assets import Accessory, Component, Consumable, Equipment
from db_inventory.models.security import UserSession
from users.factories.user_factories import User
from sites.models.sites import Department, Location, Room
from analytics.models.metrics import DailyAuthMetrics, DailyReturnMetrics, DailySystemMetrics
from analytics.models.snapshots import DailyDepartmentSnapshot



def clamp(val: int) -> int:
    return max(0, int(val))


def trend(base: int, days_ago: int, total_days: int, growth: float = 0.6) -> int:
    """
    Long-term growth curve.
    growth ~0.5 = slow growth, ~1.0 = aggressive growth
    """
    t = 1 - (days_ago / total_days)
    factor = 0.7 + (growth * t)
    return clamp(base * factor)


def weekly_seasonality(value: int, date, amplitude: float = 0.2) -> int:
    """
    Weekdays busier than weekends.
    """
    weekday = date.weekday()  # 0=Mon … 6=Sun
    factor = 1 + amplitude * (0.25 if weekday < 5 else -0.35)
    return clamp(value * factor)


def noise(value: int, pct: float = 0.15) -> int:
    return clamp(value * random.uniform(1 - pct, 1 + pct))


def incident_multiplier(chance: float = 0.03):
    """
    Rare security incidents / outages / attacks.
    """
    if random.random() < chance:
        return random.uniform(1.5, 4.0)
    return 1.0


def regime_shift(value: int, days_ago: int, period: int = 90) -> int:
    """
    Stepwise changes every N days.
    """
    shift = (days_ago // period) * random.uniform(-0.08, 0.12)
    return clamp(value * (1 + shift))


class Command(BaseCommand):
    help = "Backfill ~2 years of realistic analytics data"

    def handle(self, *args, **kwargs):

        DAYS = 730
        BATCH_SIZE = 5000
        today = timezone.localdate()

        self.stdout.write(self.style.WARNING("Clearing existing metrics…"))

        DailySystemMetrics.objects.all().delete()
        DailyAuthMetrics.objects.all().delete()
        DailyDepartmentSnapshot.objects.all().delete()
        DailyReturnMetrics.objects.all().delete()

        # ------------------------------
        # Baselines
        # ------------------------------

        baseline_users = User.objects.filter(is_active=True).count()
        baseline_sessions = UserSession.objects.count()
        baseline_equipment = Equipment.objects.count()

        baseline_failed_logins = max(10, baseline_users // 20)
        baseline_return_requests = max(5, baseline_users // 10)

        departments = list(Department.objects.all())

        # ------------------------------
        # Cache department statistics
        # ------------------------------

        dept_stats = {}

        for dept in departments:
            dept_stats[dept.id] = {
                "users": User.objects.filter(active_role__department=dept).count(),
                "locations": Location.objects.filter(department=dept).count(),
                "rooms": Room.objects.filter(location__department=dept).count(),
                "equipment": Equipment.objects.filter(
                    room__location__department=dept
                ).count(),
            }

        # ------------------------------
        # Cache inventory metrics
        # ------------------------------

        baseline_components = Component.objects.count()
        baseline_consumables = Consumable.objects.count()
        baseline_accessories = Accessory.objects.count()

        baseline_component_quantity = (
            Component.objects.aggregate(q=models.Sum("quantity"))["q"] or 0
        )
        baseline_consumable_quantity = (
            Consumable.objects.aggregate(q=models.Sum("quantity"))["q"] or 0
        )
        baseline_accessory_quantity = (
            Accessory.objects.aggregate(q=models.Sum("quantity"))["q"] or 0
        )

        system_rows = []
        auth_rows = []
        dept_rows = []
        return_rows = []

        # ------------------------------
        # Generate timeline
        # ------------------------------

        for days_ago in tqdm(range(DAYS, 0, -1), desc="Generating days"):

            date = today - datetime.timedelta(days=days_ago)

            total_users = trend(baseline_users, days_ago, DAYS, growth=0.8)

            active_users = weekly_seasonality(
                noise(int(total_users * 0.75), 0.1),
                date,
            )

            active_sessions = clamp(active_users * random.uniform(0.9, 1.4))

            system_rows.append(
                DailySystemMetrics(
                    date=date,
                    schema_version=1,

                    total_users=total_users,
                    active_users_last_24h=noise(active_users, 0.15),
                    active_users_last_7d=noise(active_users, 0.1),
                    new_users_last_24h=random.randint(0, max(1, total_users // 200)),
                    locked_users=random.randint(0, max(1, total_users // 500)),

                    total_sessions=trend(baseline_sessions, days_ago, DAYS),
                    active_sessions=active_sessions,
                    revoked_sessions=random.randint(0, active_sessions // 8),
                    expired_sessions_last_24h=random.randint(0, active_sessions // 6),
                    unique_users_logged_in_last_24h=noise(active_users, 0.1),

                    total_equipment=baseline_equipment,
                    equipment_ok=noise(int(baseline_equipment * 0.9), 0.05),
                    equipment_under_repair=noise(int(baseline_equipment * 0.07), 0.2),
                    equipment_damaged=noise(int(baseline_equipment * 0.03), 0.3),

                    total_components=baseline_components,
                    total_components_quantity=noise(baseline_component_quantity, 0.05),
                    total_consumables=baseline_consumables,
                    total_consumables_quantity=noise(baseline_consumable_quantity, 0.05),
                    total_accessories=baseline_accessories,
                    total_accessories_quantity=noise(baseline_accessory_quantity, 0.05),
                )
            )

            # ------------------------------
            # AUTH METRICS
            # ------------------------------

            incident = incident_multiplier()

            failed_logins = clamp(
                weekly_seasonality(
                    noise(baseline_failed_logins, 0.3),
                    date,
                ) * incident
            )

            lockouts = clamp(failed_logins * random.uniform(0.05, 0.15))

            auth_rows.append(
                DailyAuthMetrics(
                    date=date,
                    schema_version=1,

                    total_logins=noise(active_users, 0.2),
                    unique_users_logged_in=noise(int(active_users * 0.85), 0.1),
                    failed_logins=failed_logins,
                    lockouts=lockouts,

                    active_sessions=active_sessions,
                    revoked_sessions=random.randint(0, active_sessions // 6),
                    expired_sessions=random.randint(0, active_sessions // 4),

                    password_resets_started=random.randint(0, max(1, active_users // 150)),
                    password_resets_completed=random.randint(0, max(1, active_users // 180)),
                    active_password_resets=random.randint(0, max(1, active_users // 400)),
                    expired_password_resets=random.randint(0, max(1, active_users // 500)),
                )
            )

            # ------------------------------
            # Department metrics
            # ------------------------------

            for dept in departments:

                stats = dept_stats[dept.id]

                dept_users = stats["users"]

                dept_total_returns = clamp(
                    weekly_seasonality(
                        trend(baseline_return_requests, days_ago, DAYS, growth=0.7),
                        date,
                    )
                )

                dept_pending = int(dept_total_returns * random.uniform(0.2, 0.4))
                dept_approved = int(dept_total_returns * random.uniform(0.4, 0.6))
                dept_denied = int(dept_total_returns * random.uniform(0.05, 0.15))

                dept_partial = max(
                    0,
                    dept_total_returns - (
                        dept_pending + dept_approved + dept_denied
                    )
                )

                returns_created_24h = clamp(noise(int(dept_total_returns * 0.15), 0.3))
                returns_processed_24h = clamp(noise(int(dept_total_returns * 0.12), 0.3))

                dept_rows.append(
                    DailyDepartmentSnapshot(
                        department=dept,
                        snapshot_date=date,
                        schema_version=1,
                        created_by="backfill",

                        total_users=noise(dept_users, 0.05),
                        total_admins=random.randint(1, max(1, dept_users // 20)),

                        total_locations=stats["locations"],
                        total_rooms=stats["rooms"],
                        total_equipment=stats["equipment"],

                        equipment_ok=random.randint(10, 100),
                        equipment_under_repair=random.randint(0, 20),
                        equipment_damaged=random.randint(0, 10),

                        total_components=random.randint(100, 500),
                        total_components_quantity=random.randint(500, 5000),
                        total_consumables=random.randint(50, 200),
                        total_consumables_quantity=random.randint(500, 4000),
                        total_accessories=random.randint(30, 150),
                        total_accessories_quantity=random.randint(200, 3000),

                        total_return_requests=dept_total_returns,
                        pending_return_requests=dept_pending,
                        approved_return_requests=dept_approved,
                        denied_return_requests=dept_denied,
                        partial_return_requests=dept_partial,

                        returns_created_last_24h=returns_created_24h,
                        returns_processed_last_24h=returns_processed_24h,
                    )
                )

            # ------------------------------
            # Global return metrics
            # ------------------------------

            total_requests = clamp(
                weekly_seasonality(
                    trend(baseline_return_requests, days_ago, DAYS, growth=0.7),
                    date,
                )
            )

            pending = int(total_requests * random.uniform(0.2, 0.4))
            approved = int(total_requests * random.uniform(0.4, 0.6))
            denied = int(total_requests * random.uniform(0.05, 0.15))

            partial = max(0, total_requests - (pending + approved + denied))

            completed = approved

            created_24h = clamp(noise(int(total_requests * 0.15), 0.3))
            processed_24h = clamp(noise(int(total_requests * 0.12), 0.3))

            total_items = total_requests * random.randint(1, 4)

            pending_items = int(total_items * random.uniform(0.2, 0.4))
            approved_items = int(total_items * random.uniform(0.4, 0.6))
            denied_items = max(0, total_items - (pending_items + approved_items))

            equipment_items = int(total_items * random.uniform(0.4, 0.6))
            accessory_items = int(total_items * random.uniform(0.2, 0.4))

            consumable_items = max(
                0,
                total_items - (equipment_items + accessory_items)
            )

            avg_time = random.randint(500, 5000)
            max_time = avg_time + random.randint(1000, 10000)

            return_rows.append(
                DailyReturnMetrics(
                    date=date,

                    total_requests=total_requests,
                    pending_requests=pending,
                    approved_requests=approved,
                    denied_requests=denied,
                    partial_requests=partial,
                    completed_requests=completed,

                    requests_created_last_24h=created_24h,
                    requests_processed_last_24h=processed_24h,

                    total_items=total_items,
                    pending_items=pending_items,
                    approved_items=approved_items,
                    denied_items=denied_items,

                    equipment_items=equipment_items,
                    accessory_items=accessory_items,
                    consumable_items=consumable_items,

                    avg_processing_time_seconds=avg_time,
                    max_processing_time_seconds=max_time,

                    schema_version=1,
                )
            )

        # ------------------------------
        # Bulk insert
        # ------------------------------

        self.stdout.write(self.style.MIGRATE_HEADING("Bulk inserting rows…"))

        with transaction.atomic():

            DailySystemMetrics.objects.bulk_create(system_rows, batch_size=BATCH_SIZE)
            DailyAuthMetrics.objects.bulk_create(auth_rows, batch_size=BATCH_SIZE)
            DailyDepartmentSnapshot.objects.bulk_create(dept_rows, batch_size=BATCH_SIZE)
            DailyReturnMetrics.objects.bulk_create(return_rows, batch_size=BATCH_SIZE)

        self.stdout.write(self.style.SUCCESS("✓ Backfill complete with realistic variation"))