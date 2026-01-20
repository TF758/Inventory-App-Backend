import os
import random
import django
from datetime import timedelta
from django.utils import timezone
from django.db import transaction
from tqdm import tqdm # progress bar

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "inventory.settings")
django.setup()

from django.core.management.base import BaseCommand
from db_inventory.models.asset_assignment import ( AccessoryAssignment, AccessoryEvent, )
from db_inventory.models.assets import Accessory
from db_inventory.models.users import User


FAKE_EVENTS_PER_ACCESSORY = 50

SCENARIOS = {
    "assigned_active": 0.30,
    "assigned_returned": 0.25,
    "partial_return": 0.15,
    "condemned": 0.15,
    "restocked": 0.10,
    "adjusted": 0.05,
}

SEGMENTS_PER_ACCESSORY = (2, 4)


def next_time(current):
    return current + timedelta(days=random.randint(5, 120))


def pick_scenario():
    return random.choices(
        list(SCENARIOS.keys()),
        weights=list(SCENARIOS.values()),
    )[0]


def get_last_event_time(accessory):
    last_event = (
        AccessoryEvent.objects
        .filter(accessory=accessory)
        .order_by("-occurred_at")
        .first()
    )
    return last_event.occurred_at if last_event else None


def create_event(accessory, event_type, quantity_change, user, when, notes=""):
    AccessoryEvent.objects.create(
        accessory=accessory,
        user=user,
        reported_by=user,
        event_type=event_type,
        quantity_change=quantity_change,
        occurred_at=when,
        notes=notes,
    )

    if quantity_change != 0:
        accessory.quantity = max(0, accessory.quantity + quantity_change)
        accessory.save(update_fields=["quantity"])

def assign_accessory(accessory, user, when):
    if accessory.quantity <= 0:
        return None

    qty = random.randint(1, min(3, accessory.quantity))

    assignment = AccessoryAssignment.objects.create(
        accessory=accessory,
        user=user,
        quantity=qty,
        assigned_at=when,
        assigned_by=user,
    )

    create_event(
        accessory,
        "assigned",
        0,
        user,
        when,
        notes=f"Assigned {qty} units",
    )

    return assignment


def return_accessory(assignment, qty, when):
    qty = min(qty, assignment.quantity)

    assignment.quantity -= qty
    if assignment.quantity == 0:
        assignment.returned_at = when
    assignment.save()

    create_event(
        assignment.accessory,
        "returned",
        0,
        assignment.user,
        when,
        notes=f"Returned {qty} units",
    )



def generate_accessory_timeline(accessory, users, start_time=None):
    if start_time:
        now = start_time + timedelta(days=random.randint(7, 60))
    else:
        now = timezone.now() - timedelta(days=random.randint(300, 1500))

    scenario = pick_scenario()
    user = random.choice(users)

    if accessory.quantity == 0:
        create_event(
            accessory,
            "restocked",
            random.randint(5, 25),
            user,
            now,
            notes="Initial stock",
        )
        now = next_time(now)

    if scenario == "assigned_active":
        assign_accessory(accessory, user, now)

    elif scenario == "assigned_returned":
        assignment = assign_accessory(accessory, user, now)
        if assignment:
            return_accessory(assignment, assignment.quantity, next_time(now))

    elif scenario == "partial_return":
        assignment = assign_accessory(accessory, user, now)
        if assignment and assignment.quantity > 1:
            return_accessory(
                assignment,
                random.randint(1, assignment.quantity - 1),
                next_time(now),
            )

    elif scenario == "condemned":
        condemned = random.randint(1, min(3, accessory.quantity))
        create_event(
            accessory,
            "condemned",
            -condemned,
            user,
            now,
            notes="Damaged beyond repair",
        )

    elif scenario == "restocked":
        create_event(
            accessory,
            "restocked",
            random.randint(5, 20),
            user,
            now,
            notes="Supplier delivery",
        )

    elif scenario == "adjusted":
        delta = random.choice([-2, -1, 1, 2])
        create_event(
            accessory,
            "adjusted",
            delta,
            user,
            now,
            notes="Inventory recount adjustment",
        )


def generate_multiple_timelines(accessory, users, segments):
    current_time = None

    for _ in range(segments):
        generate_accessory_timeline(accessory, users, current_time)
        current_time = get_last_event_time(accessory)
        if current_time:
            current_time += timedelta(days=random.randint(20, 120))


def bulk_fake_events(accessory, users, start_time, count):
    events = []
    current_time = start_time

    for _ in range(count):
        current_time += timedelta(minutes=random.randint(5, 240))
        events.append(
            AccessoryEvent(
                accessory=accessory,
                user=random.choice(users),
                reported_by=random.choice(users),
                event_type=random.choice(
                    ["assigned", "returned", "adjusted"]
                ),
                quantity_change=0,
                occurred_at=current_time,
                notes="Synthetic historical event",
            )
        )

    AccessoryEvent.objects.bulk_create(events)


# -------------------------------
# Management command
# -------------------------------
class Command(BaseCommand):
    help = "Purge and regenerate accessory assignment & event history"

    def handle(self, *args, **kwargs):
        users = list(User.objects.filter(is_active=True))
        accessories = list(Accessory.objects.all())

        self.stdout.write(self.style.WARNING("Purging accessory history…"))

        with transaction.atomic():
            AccessoryAssignment.objects.all().delete()
            AccessoryEvent.objects.all().delete()

        self.stdout.write(self.style.WARNING("Existing accessory history purged."))

        self.stdout.write(
            self.style.MIGRATE_HEADING(
                f"Generating history for {len(accessories):,} accessories"
            )
        )

        for accessory in tqdm(
            accessories,
            desc="Processing accessories",
            unit="accessory",
        ):
            segments = random.randint(*SEGMENTS_PER_ACCESSORY)

            generate_multiple_timelines(accessory, users, segments)

            last_time = get_last_event_time(accessory) or timezone.now()
            bulk_fake_events(accessory, users, last_time, FAKE_EVENTS_PER_ACCESSORY)

        self.stdout.write( self.style.SUCCESS("Accessory history generation complete!") )
