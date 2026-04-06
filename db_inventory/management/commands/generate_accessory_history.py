import random
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from tqdm import tqdm

from db_inventory.models.asset_assignment import (
    AccessoryAssignment,
    AccessoryEvent,
)
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


class Command(BaseCommand):
    help = "Purge and regenerate accessory assignment & event history (bulk optimized)"

    def handle(self, *args, **kwargs):

        users = list(User.objects.filter(is_active=True))
        accessories = list(Accessory.objects.all())

        event_rows = []
        assignment_rows = []
        accessories_to_update = set()

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

        for accessory in tqdm(accessories, desc="Processing accessories"):

            current_time = timezone.now() - timedelta(
                days=random.randint(300, 1500)
            )

            segments = random.randint(*SEGMENTS_PER_ACCESSORY)

            for _ in range(segments):

                scenario = pick_scenario()
                user = random.choice(users)

                if accessory.quantity == 0:
                    qty = random.randint(5, 25)

                    accessory.quantity += qty
                    accessories_to_update.add(accessory)

                    event_rows.append(
                        AccessoryEvent(
                            accessory=accessory,
                            user=user,
                            reported_by=user,
                            event_type="restocked",
                            quantity_change=qty,
                            occurred_at=current_time,
                            notes="Initial stock",
                        )
                    )

                    current_time = next_time(current_time)

                if scenario == "assigned_active":

                    qty = min(random.randint(1, 3), accessory.quantity)

                    if qty > 0:

                        assignment = AccessoryAssignment(
                            accessory=accessory,
                            user=user,
                            quantity=qty,
                            assigned_at=current_time,
                            assigned_by=user,
                        )

                        assignment_rows.append(assignment)

                        event_rows.append(
                            AccessoryEvent(
                                accessory=accessory,
                                user=user,
                                reported_by=user,
                                event_type="assigned",
                                quantity_change=0,
                                occurred_at=current_time,
                                notes=f"Assigned {qty} units",
                            )
                        )

                elif scenario == "assigned_returned":

                    qty = min(random.randint(1, 3), accessory.quantity)

                    if qty > 0:

                        assignment = AccessoryAssignment(
                            accessory=accessory,
                            user=user,
                            quantity=qty,
                            assigned_at=current_time,
                            assigned_by=user,
                        )

                        assignment_rows.append(assignment)

                        event_rows.append(
                            AccessoryEvent(
                                accessory=accessory,
                                user=user,
                                reported_by=user,
                                event_type="assigned",
                                quantity_change=0,
                                occurred_at=current_time,
                                notes=f"Assigned {qty} units",
                            )
                        )

                        current_time = next_time(current_time)

                        event_rows.append(
                            AccessoryEvent(
                                accessory=accessory,
                                user=user,
                                reported_by=user,
                                event_type="returned",
                                quantity_change=0,
                                occurred_at=current_time,
                                notes=f"Returned {qty} units",
                            )
                        )

                elif scenario == "partial_return":

                    qty = min(random.randint(2, 3), accessory.quantity)

                    if qty > 1:

                        assignment = AccessoryAssignment(
                            accessory=accessory,
                            user=user,
                            quantity=qty,
                            assigned_at=current_time,
                            assigned_by=user,
                        )

                        assignment_rows.append(assignment)

                        event_rows.append(
                            AccessoryEvent(
                                accessory=accessory,
                                user=user,
                                reported_by=user,
                                event_type="assigned",
                                quantity_change=0,
                                occurred_at=current_time,
                                notes=f"Assigned {qty} units",
                            )
                        )

                        returned = random.randint(1, qty - 1)

                        current_time = next_time(current_time)

                        event_rows.append(
                            AccessoryEvent(
                                accessory=accessory,
                                user=user,
                                reported_by=user,
                                event_type="returned",
                                quantity_change=0,
                                occurred_at=current_time,
                                notes=f"Returned {returned} units",
                            )
                        )

                elif scenario == "condemned":

                    condemned = min(random.randint(1, 3), accessory.quantity)

                    accessory.quantity -= condemned
                    accessories_to_update.add(accessory)

                    event_rows.append(
                        AccessoryEvent(
                            accessory=accessory,
                            user=user,
                            reported_by=user,
                            event_type="condemned",
                            quantity_change=-condemned,
                            occurred_at=current_time,
                            notes="Damaged beyond repair",
                        )
                    )

                elif scenario == "restocked":

                    qty = random.randint(5, 20)

                    accessory.quantity += qty
                    accessories_to_update.add(accessory)

                    event_rows.append(
                        AccessoryEvent(
                            accessory=accessory,
                            user=user,
                            reported_by=user,
                            event_type="restocked",
                            quantity_change=qty,
                            occurred_at=current_time,
                            notes="Supplier delivery",
                        )
                    )

                elif scenario == "adjusted":

                    delta = random.choice([-2, -1, 1, 2])

                    accessory.quantity = max(0, accessory.quantity + delta)
                    accessories_to_update.add(accessory)

                    event_rows.append(
                        AccessoryEvent(
                            accessory=accessory,
                            user=user,
                            reported_by=user,
                            event_type="adjusted",
                            quantity_change=delta,
                            occurred_at=current_time,
                            notes="Inventory recount adjustment",
                        )
                    )

                current_time = next_time(current_time)

            # fake activity events

            for _ in range(FAKE_EVENTS_PER_ACCESSORY):

                current_time += timedelta(minutes=random.randint(5, 240))

                event_rows.append(
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

        # -----------------------
        # Bulk database writes
        # -----------------------

        self.stdout.write(self.style.MIGRATE_HEADING("Writing history to database…"))

        with transaction.atomic():

            if assignment_rows:
                AccessoryAssignment.objects.bulk_create(
                    assignment_rows,
                    batch_size=1000,
                )

            if event_rows:
                AccessoryEvent.objects.bulk_create(
                    event_rows,
                    batch_size=2000,
                )

            if accessories_to_update:
                Accessory.objects.bulk_update(
                    list(accessories_to_update),
                    ["quantity"],
                    batch_size=1000,
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"Accessory history generation complete 🎉 "
                f"({len(event_rows):,} events)"
            )
        )