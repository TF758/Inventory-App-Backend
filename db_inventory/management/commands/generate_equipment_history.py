import os
import random
import django
from faker import Faker
from datetime import timedelta
from django.utils import timezone
from tqdm import tqdm  # ✅ progress bar

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "inventory.settings")
django.setup()

from django.core.management.base import BaseCommand
from django.db import transaction

from db_inventory.models.asset_assignment import (
    EquipmentAssignment,
    EquipmentEvent,
)
from db_inventory.models.assets import Equipment
from db_inventory.models.users import User

faker = Faker()

# -------------------------------
# Scenario configuration
# -------------------------------

FAKE_EVENTS_PER_EQUIPMENT = 50

SCENARIOS = {
    "assigned_active": 0.20,
    "assigned_returned": 0.20,
    "reassigned": 0.20,
    "damaged_repaired": 0.20,
    "lost_or_retired": 0.20,
}

EVENT_TO_STATUS = {
    "assigned": "ok",
    "returned": "ok",
    "damaged": "damaged",
    "repaired": "ok",
    "lost": "lost",
    "retired": "retired",
}

SEGMENTS_PER_EQUIPMENT = (2, 4)


# -------------------------------
# Helpers
# -------------------------------
def pick_scenario():
    return random.choices(
        list(SCENARIOS.keys()),
        weights=list(SCENARIOS.values()),
    )[0]


def next_time(current):
    return current + timedelta(days=random.randint(10, 180))


def get_last_event_time(equipment):
    last_event = (
        EquipmentEvent.objects
        .filter(equipment=equipment)
        .order_by("-occurred_at")
        .first()
    )
    return last_event.occurred_at if last_event else None


def create_event(equipment, event_type, user, when):
    EquipmentEvent.objects.create(
        equipment=equipment,
        user=user,
        reported_by=user,
        event_type=event_type,
        occurred_at=when,
    )

    equipment.status = EVENT_TO_STATUS[event_type]
    equipment.save(update_fields=["status"])


# -------------------------------
# Assignment logic
# -------------------------------
def assign_equipment(equipment, user, when):
    if equipment.is_assigned:
        return

    assignment, created = EquipmentAssignment.objects.get_or_create(
        equipment=equipment,
        defaults={
            "user": user,
            "assigned_by": user,
            "assigned_at": when,
        },
    )

    if not created:
        assignment.user = user
        assignment.assigned_at = when
        assignment.returned_at = None
        assignment.save()

    create_event(equipment, "assigned", user, when)


def unassign_equipment(equipment, when):
    if not equipment.is_assigned:
        return

    assignment = equipment.active_assignment
    assignment.returned_at = when
    assignment.save(update_fields=["returned_at"])

    create_event(equipment, "returned", assignment.user, when)


def reassign_equipment(equipment, new_user, when):
    if not equipment.is_assigned:
        assign_equipment(equipment, new_user, when)
        return

    assignment = equipment.active_assignment
    old_user = assignment.user

    create_event(equipment, "returned", old_user, when)

    assignment.user = new_user
    assignment.assigned_by = new_user
    assignment.assigned_at = when
    assignment.returned_at = None
    assignment.save()

    create_event(equipment, "assigned", new_user, when)


# -------------------------------
# Timeline generation
# -------------------------------
def generate_timeline(equipment, users, start_time=None):
    if start_time:
        now = start_time + timedelta(days=random.randint(7, 60))
    else:
        now = timezone.now() - timedelta(days=random.randint(500, 1800))

    scenario = pick_scenario()
    user = random.choice(users)

    if scenario == "assigned_active":
        assign_equipment(equipment, user, now)

    elif scenario == "assigned_returned":
        assign_equipment(equipment, user, now)
        unassign_equipment(equipment, next_time(now))

    elif scenario == "reassigned":
        assign_equipment(equipment, user, now)
        reassign_equipment(equipment, random.choice(users), next_time(now))

    elif scenario == "damaged_repaired":
        assign_equipment(equipment, user, now)
        create_event(equipment, "damaged", user, next_time(now))
        create_event(equipment, "repaired", user, next_time(now))

    elif scenario == "lost_or_retired":
        assign_equipment(equipment, user, now)
        create_event(
            equipment,
            random.choice(["lost", "retired"]),
            user,
            next_time(now),
        )


def generate_multiple_timelines(equipment, users, segments):
    current_time = None

    for _ in range(segments):
        generate_timeline(
            equipment,
            users,
            start_time=current_time,
        )

        current_time = get_last_event_time(equipment)
        if current_time:
            current_time += timedelta(days=random.randint(30, 120))


# -------------------------------
# Bulk fake events
# -------------------------------
def bulk_fake_events(equipment, users, start_time, count):
    events = []
    current_time = start_time

    for _ in range(count):
        current_time += timedelta(minutes=random.randint(5, 240))
        events.append(
            EquipmentEvent(
                equipment=equipment,
                user=random.choice(users),
                reported_by=random.choice(users),
                event_type=random.choice(
                    ["assigned", "returned", "inspected", "commented"]
                ),
                occurred_at=current_time,
                notes="Synthetic historical event",
            )
        )

    EquipmentEvent.objects.bulk_create(events)


# -------------------------------
# Management command
# -------------------------------
class Command(BaseCommand):
    help = "Purge and regenerate equipment assignment & event history"

    def handle(self, *args, **kwargs):
        users = list(User.objects.filter(is_active=True))
        equipments = list(Equipment.objects.all())

        self.stdout.write(self.style.WARNING("Purging equipment history…"))

        with transaction.atomic():
            EquipmentAssignment.objects.all().delete()
            EquipmentEvent.objects.all().delete()

        self.stdout.write(self.style.WARNING("Existing equipment history purged."))

        self.stdout.write(
            self.style.MIGRATE_HEADING(
                f"Generating history for {len(equipments):,} equipment items"
            )
        )

        for equipment in tqdm(
            equipments,
            desc="Processing equipment",
            unit="equipment",
        ):
            segments = random.randint(*SEGMENTS_PER_EQUIPMENT)

            generate_multiple_timelines(
                equipment,
                users,
                segments=segments,
            )

            last_time = get_last_event_time(equipment) or timezone.now()

            bulk_fake_events(
                equipment=equipment,
                users=users,
                start_time=last_time,
                count=FAKE_EVENTS_PER_EQUIPMENT,
            )

        self.stdout.write(
            self.style.SUCCESS("Equipment history generation complete 🎉")
        )
