import os
import random
import django
from faker import Faker
from datetime import timedelta
import random
from django.utils import timezone
from db_inventory.models.asset_assignment import AccessoryAssignment, AccessoryEvent
from db_inventory.models.assets import Accessory
from db_inventory.models.users import User

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "inventory.settings")
django.setup()


from django.core.management import call_command
from django.core.management.base import BaseCommand

SCENARIOS = {
    "assigned_active": 0.30,        # assigned, not returned
    "assigned_returned": 0.25,      # assigned then returned
    "partial_return": 0.15,         # assigned, partially returned
    "condemned": 0.15,              # stock condemned
    "restocked": 0.10,              # new stock added
    "adjusted": 0.05,               # inventory correction
}


def next_time(current):
    return current + timedelta(days=random.randint(5, 120))

def pick_scenario():
    scenarios = list(SCENARIOS.keys())
    weights = list(SCENARIOS.values())
    return random.choices(scenarios, weights=weights)[0]

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

    # Apply ownership change
    if quantity_change != 0:
        accessory.quantity += quantity_change
        if accessory.quantity < 0:
            accessory.quantity = 0
        accessory.save(update_fields=["quantity"])

def assign_accessory(accessory, user, when):
    if accessory.quantity <= 0:
        return

    qty = random.randint(1, min(3, accessory.quantity))

    AccessoryAssignment.objects.create(
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

    return qty


def return_accessory(assignment, qty, when):
    if qty > assignment.quantity:
        qty = assignment.quantity

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


def generate_accessory_timeline(accessory, users):
    now = timezone.now() - timedelta(days=random.randint(180, 1200))
    scenario = random.choices(
        list(SCENARIOS.keys()),
        weights=list(SCENARIOS.values()),
    )[0]

    user = random.choice(users)

    # Ensure starting stock
    if accessory.quantity == 0:
        create_event(
            accessory,
            "restocked",
            random.randint(5, 20),
            user,
            now,
            notes="Initial stock",
        )
        now = next_time(now)

    if scenario == "assigned_active":
        assign_accessory(accessory, user, now)

    elif scenario == "assigned_returned":
        qty = assign_accessory(accessory, user, now)
        if qty:
            now = next_time(now)
            assignment = AccessoryAssignment.objects.filter(
                accessory=accessory,
                user=user,
                returned_at__isnull=True,
            ).last()
            return_accessory(assignment, qty, now)

    elif scenario == "partial_return":
        qty = assign_accessory(accessory, user, now)
        if qty and qty > 1:
            now = next_time(now)
            assignment = AccessoryAssignment.objects.filter(
                accessory=accessory,
                user=user,
                returned_at__isnull=True,
            ).last()
            return_accessory(assignment, random.randint(1, qty - 1), now)

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
            random.randint(5, 15),
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

class Command(BaseCommand):
    help = "Generate historical accessory assignments and events"

    def handle(self, *args, **kwargs):
        accessories = Accessory.objects.all()
        users = list(User.objects.filter(is_active=True))

        self.stdout.write(
            f"Generating history for {accessories.count()} accessories"
        )

        for accessory in accessories:
            if AccessoryEvent.objects.filter(accessory=accessory).exists():
                continue

            generate_accessory_timeline(accessory, users)

        self.stdout.write(
            self.style.SUCCESS("Accessory history generation complete")
        )