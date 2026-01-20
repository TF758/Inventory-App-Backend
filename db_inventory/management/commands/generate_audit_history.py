import os
import profile
import random
import django
from datetime import timedelta, date
from collections import defaultdict

from django.utils import timezone
from django.db import transaction
from tqdm import tqdm 

from db_inventory.factories import AuditLogFactory
from db_inventory.models.assets import Consumable, Equipment
from db_inventory.models.roles import RoleAssignment

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "inventory.settings")
django.setup()

from django.core.management.base import BaseCommand

from db_inventory.models.audit import AuditLog
from db_inventory.models.users import User
from db_inventory.utils.ids import generate_prefixed_id




DEFAULT_YEARS = 3
BATCH_SIZE = 1000

EVENT_RATE_BY_AGE = [
    (36, 3),
    (24, 10),
    (12, 25),
    (3, 60),
    (0, 120),
]

EVENT_WEIGHTS = {
    AuditLog.Events.LOGIN: 20,
    AuditLog.Events.LOGOUT: 10,
    AuditLog.Events.MODEL_UPDATED: 15,
    AuditLog.Events.ASSET_ASSIGNED: 10,
    AuditLog.Events.ASSET_RETURNED: 10,
    AuditLog.Events.CONSUMABLE_USED: 15,
    AuditLog.Events.EXPORT_GENERATED: 5,
    AuditLog.Events.ROLE_ASSIGNED: 3,
    AuditLog.Events.ROLE_REVOKED: 2,
    AuditLog.Events.USER_CREATED: 3,
    AuditLog.Events.USER_UPDATED: 5,
    AuditLog.Events.USER_DELETED: 1,
}

EVENT_PROFILES = {
    AuditLog.Events.LOGIN: {
        "target": None,
        "org_scope": False,
    },
    AuditLog.Events.LOGOUT: {
        "target": None,
        "org_scope": False,
    },
    AuditLog.Events.USER_CREATED: {
        "target": "user",
        "org_scope": False,
    },
    AuditLog.Events.USER_UPDATED: {
        "target": "user",
        "org_scope": False,
    },
    AuditLog.Events.ROLE_ASSIGNED: {
        "target": "role",
        "org_scope": True,
    },
    AuditLog.Events.ROLE_REVOKED: {
        "target": "role",
        "org_scope": True,
    },
    AuditLog.Events.ASSET_ASSIGNED: {
        "target": "equipment",
        "org_scope": True,
    },
    AuditLog.Events.ASSET_RETURNED: {
        "target": "equipment",
        "org_scope": True,
    },
    AuditLog.Events.CONSUMABLE_USED: {
        "target": "consumable",
        "org_scope": True,
    },
    AuditLog.Events.EXPORT_GENERATED: {
        "target": None,
        "org_scope": True,
    },
}
# Helpers

def safe_str(value, max_len):
    if value is None:
        return None
    return str(value)[:max_len]


def months_ago(dt):
    today = date.today()
    return (today.year - dt.year) * 12 + (today.month - dt.month)


def daily_event_count(day):
    age_months = months_ago(day)
    for cutoff, rate in EVENT_RATE_BY_AGE:
        if age_months >= cutoff:
            return random.randint(int(rate * 0.6), int(rate * 1.4))
    return 5


def pick_event_type():
    events = list(EVENT_WEIGHTS.keys())
    weights = list(EVENT_WEIGHTS.values())
    return random.choices(events, weights=weights)[0]


def assign_public_ids(logs):
    used = set()
    for log in logs:
        while True:
            candidate = generate_prefixed_id("LOG")
            if candidate not in used:
                log.public_id = candidate
                used.add(candidate)
                break
def resolve_org_context(user):
    role = getattr(user, "active_role", None)
    if not role:
        return {}

    if role.room:
        loc = role.room.location
        dept = loc.department
        return {
            "department": dept,
            "department_name": safe_str(dept.name, 100),
            "location": loc,
            "location_name": safe_str(loc.name, 255),
            "room": role.room,
            "room_name": safe_str(role.room.name, 255),
        }

    if role.location:
        dept = role.location.department
        return {
            "department": dept,
            "department_name": safe_str(dept.name, 100),
            "location": role.location,
            "location_name": safe_str(role.location.name, 255),
        }

    if role.department:
        return {
            "department": role.department,
            "department_name": safe_str(role.department.name, 100),
        }

    return {}
def resolve_target_snapshot(event_type, user, context):
    """
    Returns safe target_* fields for AuditLogFactory.
    """

    if event_type in {
        AuditLog.Events.ASSET_ASSIGNED,
        AuditLog.Events.ASSET_RETURNED,
        AuditLog.Events.ASSET_REASSIGNED,
        AuditLog.Events.EQUIPMENT_STATUS_CHANGED,
    } and context["equipment"]:

        asset = random.choice(context["equipment"])
        return {
            "target_model": safe_str("equipment", 100),
            "target_id": safe_str(asset.public_id, 100),
            "target_name": safe_str(asset.name, 255),
        }


    if event_type in {
        AuditLog.Events.ROLE_ASSIGNED,
        AuditLog.Events.ROLE_REVOKED,
    } and context["roles"]:

        role = random.choice(context["roles"])
        return {
            "target_model": safe_str("role_assignment", 100),
            "target_id": safe_str(role.public_id, 100),
            "target_name": safe_str(role.get_role_display(), 255),
        }

    if event_type.startswith("user_"):
        return {
            "target_model": safe_str("user", 100),
            "target_id": safe_str(user.public_id, 100),
            "target_name": safe_str(user.email, 255),
        }

    return {
        "target_model": None,
        "target_id": None,
        "target_name": None,
    }
# -------------------------------
# Management command
# -------------------------------
class Command(BaseCommand):
    help = "Seed realistic audit logs for N years ending today"

    def add_arguments(self, parser):
        parser.add_argument(
            "--years",
            type=int,
            default=DEFAULT_YEARS,
            help="Number of years of audit logs to generate",
        )
        parser.add_argument(
            "--append",
            action="store_true",
            help="Append to existing audit logs instead of clearing them",
        )

    def handle(self, *args, **options):
        context = {
        "equipment": list(Equipment.objects.all()),
        "consumables": list(Consumable.objects.all()),
        "roles": list(RoleAssignment.objects.all()),
        }
        append = options["append"]
        years = options["years"]

        if not append:
            self.stdout.write("Clearing existing audit logs…")
            with transaction.atomic():
                AuditLog.objects.all().delete()
            self.stdout.write(self.style.WARNING("Existing audit logs cleared."))
        else:
            self.stdout.write(
                self.style.WARNING("Appending to existing audit logs (no purge).")
            )

        users = list(User.objects.filter(is_active=True))
        if not users:
            raise RuntimeError("No active users found")

        start_date = date.today() - timedelta(days=365 * years)
        end_date = date.today()
        total_days = (end_date - start_date).days + 1

        self.stdout.write(
            self.style.MIGRATE_HEADING(
                f"Generating audit logs for {years} years ({total_days:,} days)"
            )
        )

        total_logs = 0

        for day_offset in tqdm(
        range(total_days),
        desc="Generating audit logs",
        unit="day",
        ):
            current_day = start_date + timedelta(days=day_offset)
            count = daily_event_count(current_day)
            logs = []

            for _ in range(count):
                user = random.choice(users)
                event_type = pick_event_type()

                timestamp = timezone.make_aware(
                    timezone.datetime.combine(
                        current_day,
                        timezone.datetime.min.time()
                    )
                ) + timedelta(minutes=random.randint(0, 1440))
                profile = EVENT_PROFILES.get(event_type, {})
                
                target_data = (
                    resolve_target_snapshot(event_type, user, context)
                    if profile.get("target")
                    else {}
                )

                org_data = (
                    resolve_org_context(user)
                    if profile.get("org_scope")
                    else {})
    
                logs.append(
                    AuditLogFactory.build(
                        user=user,
                        user_public_id=user.public_id,
                        user_email=user.email,
                        event_type=event_type,
                        description=event_type.replace("_", " ").title(),
                        created_at=timestamp,
                        metadata={
                            "source": "synthetic_seed",
                            "confidence": "high",
                        },
                        **target_data,
                        **org_data,
                    )
                )

            if logs:
                assign_public_ids(logs)
                AuditLog.objects.bulk_create(
                    logs,
                    batch_size=BATCH_SIZE,
                )
                total_logs += len(logs)

            if current_day.day == 1:
                self.stdout.write(
                    f"  {current_day:%Y-%m} → total logs: {total_logs:,}"
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"Audit log seeding complete 🎉 ({total_logs:,} records)"
            )
        )
