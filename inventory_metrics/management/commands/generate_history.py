import datetime
import random
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction, models
from db_inventory.models import (
    Department, Location, User, UserSession,
    Equipment, Component, Consumable, Accessory
)
from tqdm import tqdm

from db_inventory.models.site import Room
from inventory_metrics.models.metrics import DailyAuthMetrics
from inventory_metrics.models import (
    DailySystemMetrics,
    DailyDepartmentSnapshot,
)





class Command(BaseCommand):
    help = "Backfill ~2 years of historical metrics (system/auth/department)"

    def handle(self, *args, **kwargs):
        DAYS = 730
        BATCH_SIZE = 5000
        today = timezone.localdate()

        def vary(value: int, pct: float = 0.05) -> int:
            return max(0, int(value * random.uniform(1 - pct, 1 + pct)))

        def decay(value: int, days_ago: int, daily_decay: float = 0.001) -> int:
            factor = max(0.6, 1 - days_ago * daily_decay)
            return max(0, int(value * factor))

        # -------------------------------------------------
        # 1) Clear existing metrics
        # -------------------------------------------------
        self.stdout.write(self.style.WARNING("Clearing old metric history..."))
        DailySystemMetrics.objects.all().delete()
        DailyAuthMetrics.objects.all().delete()
        DailyDepartmentSnapshot.objects.all().delete()
        self.stdout.write(self.style.SUCCESS("Metrics cleared."))

        # -------------------------------------------------
        # 2) Baseline (computed once)
        # -------------------------------------------------
        self.stdout.write(self.style.MIGRATE_HEADING("Computing baselines..."))

        baseline_system = {
            "total_users": User.objects.count(),
            "active_users": User.objects.filter(is_active=True).count(),
            "locked_users": User.objects.filter(is_locked=True).count(),

            "total_sessions": UserSession.objects.count(),
            "active_sessions": UserSession.objects.filter(status=UserSession.Status.ACTIVE).count(),
            "revoked_sessions": UserSession.objects.filter(status=UserSession.Status.REVOKED).count(),

            "total_equipment": Equipment.objects.count(),
            "equipment_ok": Equipment.objects.filter(status="ok").count(),
            "equipment_under_repair": Equipment.objects.filter(status="under_repair").count(),
            "equipment_damaged": Equipment.objects.filter(status="damaged").count(),

            "total_components": Component.objects.count(),
            "total_components_quantity": Component.objects.aggregate(q=models.Sum("quantity"))["q"] or 0,

            "total_consumables": Consumable.objects.count(),
            "total_consumables_quantity": Consumable.objects.aggregate(q=models.Sum("quantity"))["q"] or 0,

            "total_accessories": Accessory.objects.count(),
            "total_accessories_quantity": Accessory.objects.aggregate(q=models.Sum("quantity"))["q"] or 0,
        }

        baseline_auth = {
            "total_logins": baseline_system["active_users"],
            "unique_users_logged_in": int(baseline_system["active_users"] * 0.8),
            "failed_logins": max(10, baseline_system["active_users"] // 20),
            "lockouts": max(1, baseline_system["active_users"] // 200),

            "active_sessions": baseline_system["active_sessions"],
            "revoked_sessions": baseline_system["revoked_sessions"],
            "expired_sessions": baseline_system["total_sessions"] // 10,

            "password_resets_started": max(1, baseline_system["active_users"] // 100),
            "password_resets_completed": max(1, baseline_system["active_users"] // 120),
            "active_password_resets": max(0, baseline_system["active_users"] // 300),
            "expired_password_resets": max(0, baseline_system["active_users"] // 400),
        }

        departments = list(Department.objects.all())
        if not departments:
            self.stdout.write(self.style.WARNING("No departments found; department snapshots will be empty."))

        baseline_departments: dict[int, dict[str, int]] = {}

        for dept in departments:
            baseline_departments[dept.id] = {
                # NOTE: you may prefer UserLocation-based membership; this keeps your earlier approach
                "total_users": User.objects.filter(active_role__department=dept).count(),
                "total_admins": User.objects.filter(
                    role_assignments__department=dept,
                    role__endswith="ADMIN",
                ).distinct().count(),

                "total_locations": Location.objects.filter(department=dept).count(),
                "total_rooms": Room.objects.filter(location__department=dept).count(),

                "total_equipment": Equipment.objects.filter(room__location__department=dept).count(),
                "equipment_ok": Equipment.objects.filter(room__location__department=dept, status="ok").count(),
                "equipment_under_repair": Equipment.objects.filter(room__location__department=dept, status="under_repair").count(),
                "equipment_damaged": Equipment.objects.filter(room__location__department=dept, status="damaged").count(),

                "total_components": Component.objects.filter(equipment__room__location__department=dept).count(),
                "total_components_quantity": Component.objects.filter(
                    equipment__room__location__department=dept
                ).aggregate(q=models.Sum("quantity"))["q"] or 0,

                "total_consumables": Consumable.objects.filter(room__location__department=dept).count(),
                "total_consumables_quantity": Consumable.objects.filter(
                    room__location__department=dept
                ).aggregate(q=models.Sum("quantity"))["q"] or 0,

                "total_accessories": Accessory.objects.filter(room__location__department=dept).count(),
                "total_accessories_quantity": Accessory.objects.filter(
                    room__location__department=dept
                ).aggregate(q=models.Sum("quantity"))["q"] or 0,
            }

        # -------------------------------------------------
        # 3) Generate ~2 years of rows
        # -------------------------------------------------
        self.stdout.write(self.style.MIGRATE_HEADING(f"Generating {DAYS} days of history..."))

        system_rows = []
        auth_rows = []
        dept_rows = []

        for days_ago in tqdm(
            range(DAYS, 0, -1),
            desc="Generating daily metrics",
            unit="day",
        ):
            date = today - datetime.timedelta(days=days_ago)

            system_rows.append(
                DailySystemMetrics(
                    date=date,
                    schema_version=1,

                    total_users=decay(baseline_system["total_users"], days_ago),
                    active_users_last_24h=vary(baseline_system["active_users"], 0.10),
                    active_users_last_7d=vary(baseline_system["active_users"], 0.05),
                    new_users_last_24h=random.randint(0, max(1, baseline_system["total_users"] // 100)),
                    locked_users=vary(baseline_system["locked_users"], 0.10),

                    total_sessions=decay(baseline_system["total_sessions"], days_ago),
                    active_sessions=vary(baseline_system["active_sessions"], 0.10),
                    revoked_sessions=vary(baseline_system["revoked_sessions"], 0.15),
                    expired_sessions_last_24h=random.randint(0, max(1, baseline_system["total_sessions"] // 20)),
                    unique_users_logged_in_last_24h=vary(baseline_system["active_users"], 0.10),

                    total_equipment=baseline_system["total_equipment"],
                    equipment_ok=vary(baseline_system["equipment_ok"], 0.05),
                    equipment_under_repair=vary(baseline_system["equipment_under_repair"], 0.15),
                    equipment_damaged=vary(baseline_system["equipment_damaged"], 0.15),

                    total_components=baseline_system["total_components"],
                    total_components_quantity=vary(baseline_system["total_components_quantity"], 0.03),
                    total_consumables=baseline_system["total_consumables"],
                    total_consumables_quantity=vary(baseline_system["total_consumables_quantity"], 0.03),
                    total_accessories=baseline_system["total_accessories"],
                    total_accessories_quantity=vary(baseline_system["total_accessories_quantity"], 0.03),
                )
            )

            auth_rows.append(
                DailyAuthMetrics(
                    date=date,
                    schema_version=1,

                    total_logins=vary(baseline_auth["total_logins"], 0.20),
                    unique_users_logged_in=vary(baseline_auth["unique_users_logged_in"], 0.15),
                    failed_logins=random.randint(0, baseline_auth["failed_logins"] * 2),
                    lockouts=random.randint(0, baseline_auth["lockouts"] * 2),

                    active_sessions=vary(baseline_auth["active_sessions"], 0.10),
                    revoked_sessions=vary(baseline_auth["revoked_sessions"], 0.15),
                    expired_sessions=random.randint(0, max(1, baseline_auth["expired_sessions"])),

                    password_resets_started=random.randint(0, baseline_auth["password_resets_started"] * 2),
                    password_resets_completed=random.randint(0, baseline_auth["password_resets_completed"] * 2),
                    active_password_resets=random.randint(0, baseline_auth["active_password_resets"] * 2),
                    expired_password_resets=random.randint(0, baseline_auth["expired_password_resets"] * 2),
                )
            )

            for dept in tqdm(
                departments,
                desc=f"Departments ({date})",
                leave=False,
            ):
                base = baseline_departments[dept.id]
                dept_rows.append(
                    DailyDepartmentSnapshot(
                        department=dept,
                        snapshot_date=date,
                        schema_version=1,
                        created_by="backfill",

                        total_users=vary(base["total_users"], 0.05),
                        total_admins=vary(base["total_admins"], 0.10),

                        total_locations=base["total_locations"],
                        total_rooms=base["total_rooms"],

                        total_equipment=base["total_equipment"],
                        equipment_ok=vary(base["equipment_ok"], 0.05),
                        equipment_under_repair=vary(base["equipment_under_repair"], 0.10),
                        equipment_damaged=vary(base["equipment_damaged"], 0.10),

                        total_components=base["total_components"],
                        total_components_quantity=vary(base["total_components_quantity"], 0.05),
                        total_consumables=base["total_consumables"],
                        total_consumables_quantity=vary(base["total_consumables_quantity"], 0.05),
                        total_accessories=base["total_accessories"],
                        total_accessories_quantity=vary(base["total_accessories_quantity"], 0.05),
                    )
                )

        # -------------------------------------------------
        # 4) Bulk insert
        # -------------------------------------------------
        self.stdout.write(self.style.MIGRATE_HEADING("Bulk inserting rows..."))

        with transaction.atomic():
            DailySystemMetrics.objects.bulk_create(system_rows, batch_size=BATCH_SIZE)
            DailyAuthMetrics.objects.bulk_create(auth_rows, batch_size=BATCH_SIZE)
            DailyDepartmentSnapshot.objects.bulk_create(dept_rows, batch_size=BATCH_SIZE)

        self.stdout.write(self.style.SUCCESS("✓ Backfill complete (system/auth/department)."))