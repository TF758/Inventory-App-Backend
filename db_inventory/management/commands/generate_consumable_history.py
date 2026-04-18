import random
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from tqdm import tqdm

from assignments.models.asset_assignment import (
    ConsumableEvent,
    ConsumableIssue,
)
from db_inventory.models.assets import Consumable
from db_inventory.models.users import User


FAKE_EVENTS_PER_CONSUMABLE = 50

SCENARIOS = {
    "issued_active": 0.30,
    "issued_used": 0.25,
    "partial_used": 0.15,
    "condemned": 0.10,
    "expired": 0.05,
    "restocked": 0.10,
    "adjusted": 0.05,
}

SEGMENTS_PER_CONSUMABLE = (2, 4)


def next_time(current):
    return current + timedelta(days=random.randint(5, 90))


def pick_scenario():
    return random.choices(
        list(SCENARIOS.keys()),
        weights=list(SCENARIOS.values()),
    )[0]


class Command(BaseCommand):
    help = "Purge and regenerate consumable issue & event history (bulk optimized)"

    def handle(self, *args, **kwargs):

        users = list(User.objects.filter(is_active=True))
        consumables = list(Consumable.objects.all())

        event_rows = []
        issue_rows = []
        consumables_to_update = set()

        self.stdout.write(self.style.WARNING("Purging consumable history…"))

        with transaction.atomic():
            ConsumableIssue.objects.all().delete()
            ConsumableEvent.objects.all().delete()

        self.stdout.write(self.style.WARNING("Existing consumable history purged."))

        self.stdout.write(
            self.style.MIGRATE_HEADING(
                f"Generating history for {len(consumables):,} consumables"
            )
        )

        for consumable in tqdm(consumables, desc="Processing consumables"):

            current_time = timezone.now() - timedelta(
                days=random.randint(300, 1500)
            )

            segments = random.randint(*SEGMENTS_PER_CONSUMABLE)

            for _ in range(segments):

                scenario = pick_scenario()
                user = random.choice(users)

                if consumable.quantity == 0:
                    restock_qty = random.randint(15, 40)

                    consumable.quantity += restock_qty
                    consumables_to_update.add(consumable)

                    event_rows.append(
                        ConsumableEvent(
                            consumable=consumable,
                            user=user,
                            reported_by=user,
                            event_type=ConsumableEvent.EventType.RESTOCKED,
                            quantity=restock_qty,
                            quantity_change=restock_qty,
                            occurred_at=current_time,
                            notes="Initial stock",
                        )
                    )

                    current_time = next_time(current_time)

                if scenario.startswith("issued"):

                    qty = min(random.randint(1, 5), consumable.quantity)

                    if qty > 0:

                        issue = ConsumableIssue(
                            consumable=consumable,
                            user=user,
                            quantity=qty,
                            issued_quantity=qty,
                            assigned_at=current_time,
                            assigned_by=user,
                            purpose="Generated historical issue",
                        )

                        issue_rows.append(issue)

                        consumable.quantity -= qty
                        consumables_to_update.add(consumable)

                        event_rows.append(
                            ConsumableEvent(
                                consumable=consumable,
                                issue=issue,
                                user=user,
                                reported_by=user,
                                event_type=ConsumableEvent.EventType.ISSUED,
                                quantity=qty,
                                quantity_change=-qty,
                                occurred_at=current_time,
                                notes=f"Issued {qty} units",
                            )
                        )

                        if scenario == "issued_used":

                            current_time = next_time(current_time)

                            event_rows.append(
                                ConsumableEvent(
                                    consumable=consumable,
                                    issue=issue,
                                    user=user,
                                    reported_by=user,
                                    event_type=ConsumableEvent.EventType.USED,
                                    quantity=qty,
                                    quantity_change=0,
                                    occurred_at=current_time,
                                    notes=f"Used {qty} units",
                                )
                            )

                        elif scenario == "partial_used":

                            used = random.randint(1, qty - 1)

                            current_time = next_time(current_time)

                            event_rows.append(
                                ConsumableEvent(
                                    consumable=consumable,
                                    issue=issue,
                                    user=user,
                                    reported_by=user,
                                    event_type=ConsumableEvent.EventType.USED,
                                    quantity=used,
                                    quantity_change=0,
                                    occurred_at=current_time,
                                    notes=f"Used {used} units",
                                )
                            )

                elif scenario == "condemned":

                    qty = min(random.randint(1, 5), consumable.quantity)

                    consumable.quantity -= qty
                    consumables_to_update.add(consumable)

                    event_rows.append(
                        ConsumableEvent(
                            consumable=consumable,
                            user=user,
                            reported_by=user,
                            event_type=ConsumableEvent.EventType.CONDEMNED,
                            quantity=qty,
                            quantity_change=-qty,
                            occurred_at=current_time,
                            notes="Condemned stock",
                        )
                    )

                elif scenario == "expired":

                    qty = min(random.randint(1, 5), consumable.quantity)

                    consumable.quantity -= qty
                    consumables_to_update.add(consumable)

                    event_rows.append(
                        ConsumableEvent(
                            consumable=consumable,
                            user=user,
                            reported_by=user,
                            event_type=ConsumableEvent.EventType.EXPIRED,
                            quantity=qty,
                            quantity_change=-qty,
                            occurred_at=current_time,
                            notes="Expired stock",
                        )
                    )

                elif scenario == "restocked":

                    qty = random.randint(10, 30)

                    consumable.quantity += qty
                    consumables_to_update.add(consumable)

                    event_rows.append(
                        ConsumableEvent(
                            consumable=consumable,
                            user=user,
                            reported_by=user,
                            event_type=ConsumableEvent.EventType.RESTOCKED,
                            quantity=qty,
                            quantity_change=qty,
                            occurred_at=current_time,
                            notes="Supplier delivery",
                        )
                    )

                elif scenario == "adjusted":

                    delta = random.choice([-3, -2, -1, 1, 2, 3])

                    consumable.quantity = max(0, consumable.quantity + delta)
                    consumables_to_update.add(consumable)

                    event_rows.append(
                        ConsumableEvent(
                            consumable=consumable,
                            user=user,
                            reported_by=user,
                            event_type=ConsumableEvent.EventType.ADJUSTED,
                            quantity=abs(delta),
                            quantity_change=delta,
                            occurred_at=current_time,
                            notes="Inventory recount adjustment",
                        )
                    )

                current_time = next_time(current_time)

            # fake events

            for _ in range(FAKE_EVENTS_PER_CONSUMABLE):

                current_time += timedelta(minutes=random.randint(5, 240))

                event_rows.append(
                    ConsumableEvent(
                        consumable=consumable,
                        user=random.choice(users),
                        reported_by=random.choice(users),
                        event_type=random.choice(
                            [
                                ConsumableEvent.EventType.ADJUSTED,
                                ConsumableEvent.EventType.RESTOCKED,
                                ConsumableEvent.EventType.ISSUED,
                            ]
                        ),
                        quantity=0,
                        quantity_change=0,
                        occurred_at=current_time,
                        notes="Synthetic historical event",
                    )
                )

        # bulk writes

        self.stdout.write(self.style.MIGRATE_HEADING("Writing history to database…"))

        with transaction.atomic():

            if issue_rows:
                ConsumableIssue.objects.bulk_create(issue_rows, batch_size=1000)

            if event_rows:
                ConsumableEvent.objects.bulk_create(event_rows, batch_size=2000)

            if consumables_to_update:
                Consumable.objects.bulk_update(
                    list(consumables_to_update),
                    ["quantity"],
                    batch_size=1000,
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"Consumable history generation complete 🎉 "
                f"({len(event_rows):,} events)"
            )
        )