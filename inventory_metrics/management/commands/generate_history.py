import datetime
import random
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction

from db_inventory.models import (
    Department, Location, RoleAssignment, User, UserSession,
    Equipment, Component, Consumable, Accessory, UserLocation
)

from inventory_metrics.models import (
    DailySystemMetrics,
    DailySecurityMetrics,
    DailyRoleMetrics,
    DailyDepartmentSnapshot,
    DailyLocationSnapshot,
)

from inventory_metrics.factories import (
    DailySystemMetricsFactory,
    DailySecurityMetricsFactory,
    DailyRoleMetricsFactory,
    DailyDepartmentSnapshotFactory,
    DailyLocationSnapshotFactory,
)



class Command(BaseCommand):
    help = "Generate 4 months of realistic historical metrics data (bulk optimized)"

    def handle(self, *args, **kwargs):

        def vary(value, pct=0.05):
            """Adds slight natural variation to avoid flat charts."""
            return max(0, int(value * random.uniform(1 - pct, 1 + pct)))

        # -------------------------------------------------
        # 1. Flush existing metrics (safe, app-only)
        # -------------------------------------------------
        self.stdout.write(self.style.WARNING("Clearing old metric history..."))

        DailySystemMetrics.objects.all().delete()
        DailySecurityMetrics.objects.all().delete()
        DailyRoleMetrics.objects.all().delete()
        DailyDepartmentSnapshot.objects.all().delete()
        DailyLocationSnapshot.objects.all().delete()

        self.stdout.write(self.style.SUCCESS("Metrics cleared."))

        # -------------------------------------------------
        # 2. Setup
        # -------------------------------------------------
        today = timezone.now().date()
        start_date = today - datetime.timedelta(days=120)

        departments = list(Department.objects.all())
        locations = list(Location.objects.all())
        roles = [r[0] for r in RoleAssignment.ROLE_CHOICES]

        # Base values
        total_users = User.objects.count()
        total_active_users = User.objects.filter(is_active=True).count()
        total_locked_users = User.objects.filter(is_locked=True).count()

        total_sessions = UserSession.objects.count()
        active_sessions = UserSession.objects.filter(status=UserSession.Status.ACTIVE).count()
        revoked_sessions = UserSession.objects.filter(status=UserSession.Status.REVOKED).count()

        total_equipment = Equipment.objects.count()
        total_components = Component.objects.count()
        total_components_quantity = sum(c.quantity for c in Component.objects.all())
        total_consumables = Consumable.objects.count()
        total_consumables_quantity = sum(c.quantity for c in Consumable.objects.all())
        total_accessories = Accessory.objects.count()
        total_accessories_quantity = sum(a.quantity for a in Accessory.objects.all())

        system_metrics_batch = []
        security_metrics_batch = []
        role_metrics_batch = []
        dept_snapshots_batch = []
        loc_snapshots_batch = []

        # -------------------------------------------------
        # 3. Generate 4 months of fluctuating history
        # -------------------------------------------------
        for day_offset in range(121):
            snapshot_date = start_date + datetime.timedelta(days=day_offset)

            # -----------------------------
            # System metrics
            # -----------------------------
            system_metrics_batch.append(
                DailySystemMetricsFactory.build(
                    date=snapshot_date,
                    total_users=total_users,
                    active_users_last_24h=vary(total_active_users, 0.10),
                    active_users_last_7d=vary(total_active_users, 0.05),
                    new_users_last_24h=random.randint(0, max(1, total_users//80)),
                    locked_users=vary(total_locked_users, 0.10),
                    total_sessions=vary(total_sessions, 0.07),
                    active_sessions=vary(active_sessions, 0.07),
                    revoked_sessions=vary(revoked_sessions, 0.10),
                    expired_sessions_last_24h=random.randint(0, total_sessions//20),
                    unique_users_logged_in_last_24h=vary(total_active_users, 0.10),
                    total_equipment=total_equipment,
                    total_components=total_components,
                    total_components_quantity=vary(total_components_quantity, 0.03),
                    total_consumables=total_consumables,
                    total_consumables_quantity=vary(total_consumables_quantity, 0.03),
                    total_accessories=total_accessories,
                    total_accessories_quantity=vary(total_accessories_quantity, 0.03),
                )
            )

            # -----------------------------
            # Security metrics
            # allow “spike” days
            # -----------------------------
            security_metrics_batch.append(
                DailySecurityMetricsFactory.build(
                    date=snapshot_date,
                    password_resets=random.randint(0, 25),
                    active_password_resets=random.randint(0, 15),
                    expired_password_resets=random.randint(0, 8),
                    users_multiple_active_sessions=random.randint(0, 50),
                    users_with_revoked_sessions=random.randint(0, 30)
                )
            )

            # -----------------------------
            # Role metrics (vary 1–5%)
            # -----------------------------
            for role in roles:
                total_with_role = RoleAssignment.objects.filter(role=role).count()
                active_with_role = RoleAssignment.objects.filter(role=role, user__is_active=True).count()

                role_metrics_batch.append(
                    DailyRoleMetricsFactory.build(
                        date=snapshot_date,
                        role=role,
                        total_users_with_role=vary(total_with_role, 0.05),
                        total_users_active_with_role=vary(active_with_role, 0.05)
                    )
                )

            # -----------------------------
            # Department snapshots
            # -----------------------------
            for dept in departments:
                dept_users = User.objects.filter(active_role__department=dept).count()
                dept_admins = User.objects.filter(role_assignments__department=dept, role__endswith="ADMIN").count()

                dept_locations = Location.objects.filter(department=dept).count()
                dept_rooms = sum(loc.rooms.count() for loc in Location.objects.filter(department=dept))

                dept_equipment = Equipment.objects.filter(room__location__department=dept).count()
                dept_components = Component.objects.filter(equipment__room__location__department=dept).count()
                dept_components_qty = sum(c.quantity for c in Component.objects.filter(equipment__room__location__department=dept))

                dept_consumables = Consumable.objects.filter(room__location__department=dept).count()
                dept_consumables_qty = sum(c.quantity for c in Consumable.objects.filter(room__location__department=dept))

                dept_accessories = Accessory.objects.filter(room__location__department=dept).count()
                dept_accessories_qty = sum(a.quantity for a in Accessory.objects.filter(room__location__department=dept))

                dept_snapshots_batch.append(
                    DailyDepartmentSnapshotFactory.build(
                        department=dept,
                        snapshot_date=snapshot_date,
                        total_users=vary(dept_users, 0.05),
                        total_admins=vary(dept_admins, 0.10),
                        total_locations=dept_locations,
                        total_rooms=dept_rooms,
                        total_equipment=vary(dept_equipment, 0.05),
                        total_components=vary(dept_components, 0.05),
                        total_component_quantity=vary(dept_components_qty, 0.05),
                        total_consumables=vary(dept_consumables, 0.05),
                        total_consumables_quantity=vary(dept_consumables_qty, 0.05),
                        total_accessories=vary(dept_accessories, 0.05),
                        total_accessories_quantity=vary(dept_accessories_qty, 0.05),
                    )
                )

            # -----------------------------
            # Location snapshots
            # -----------------------------
            for loc in locations:
                loc_users = UserLocation.objects.filter(room__location=loc).count()
                loc_admins = User.objects.filter(role_assignments__location=loc, role__endswith="ADMIN").count()

                loc_rooms = loc.rooms.count()
                loc_equipment = Equipment.objects.filter(room__location=loc).count()
                loc_components = Component.objects.filter(equipment__room__location=loc).count()
                loc_components_qty = sum(c.quantity for c in Component.objects.filter(equipment__room__location=loc))
                loc_consumables = Consumable.objects.filter(room__location=loc).count()
                loc_consumables_qty = sum(c.quantity for c in Consumable.objects.filter(room__location=loc))
                loc_accessories = Accessory.objects.filter(room__location=loc).count()
                loc_accessories_qty = sum(a.quantity for a in Accessory.objects.filter(room__location=loc))

                loc_snapshots_batch.append(
                    DailyLocationSnapshotFactory.build(
                        location=loc,
                        snapshot_date=snapshot_date,
                        total_users=vary(loc_users, 0.05),
                        total_admins=vary(loc_admins, 0.10),
                        total_rooms=loc_rooms,
                        total_equipment=vary(loc_equipment, 0.05),
                        total_components=vary(loc_components, 0.05),
                        total_component_quantity=vary(loc_components_qty, 0.05),
                        total_consumables=vary(loc_consumables, 0.05),
                        total_consumables_quantity=vary(loc_consumables_qty, 0.05),
                        total_accessories=vary(loc_accessories, 0.05),
                        total_accessories_quantity=vary(loc_accessories_qty, 0.05),
                    )
                )

        # -------------------------------------------------
        # 4. Bulk create all data
        # -------------------------------------------------
        BATCH_SIZE = 5000

        with transaction.atomic():
            DailySystemMetrics.objects.bulk_create(system_metrics_batch, batch_size=BATCH_SIZE)
            DailySecurityMetrics.objects.bulk_create(security_metrics_batch, batch_size=BATCH_SIZE)
            DailyRoleMetrics.objects.bulk_create(role_metrics_batch, batch_size=BATCH_SIZE)
            DailyDepartmentSnapshot.objects.bulk_create(dept_snapshots_batch, batch_size=BATCH_SIZE)
            DailyLocationSnapshot.objects.bulk_create(loc_snapshots_batch, batch_size=BATCH_SIZE)

        self.stdout.write(self.style.SUCCESS("✓ 4 months of realistic historical metrics generated successfully."))
