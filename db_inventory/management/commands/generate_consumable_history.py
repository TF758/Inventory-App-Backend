import os
import random
import django
from datetime import timedelta
from django.utils import timezone
from django.db import transaction
from tqdm import tqdm  # progress bar

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "inventory.settings")
django.setup()

from django.core.management.base import BaseCommand

from db_inventory.models.asset_assignment import ( ConsumableEvent, ConsumableIssue, )
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


def get_last_event_time(consumable):
    last_event = (
        ConsumableEvent.objects
        .filter(consumable=consumable)
        .order_by("-occurred_at")
        .first()
    )
    return last_event.occurred_at if last_event else None



def create_event(
    consumable,
    event_type,
    quantity,
    quantity_change,
    user,
    when,
    issue=None,
    notes="",
):
    ConsumableEvent.objects.create(
        consumable=consumable,
        issue=issue,
        user=user,
        reported_by=user,
        event_type=event_type,
        quantity=quantity,
        quantity_change=quantity_change,
        occurred_at=when,
        notes=notes,
    )

    if quantity_change != 0:
        consumable.quantity = max(0, consumable.quantity + quantity_change)
        consumable.save(update_fields=["quantity"])



def issue_consumable(consumable, user, when):
    if consumable.quantity <= 0:
        return None

    qty = random.randint(1, min(5, consumable.quantity))

    issue = ConsumableIssue.objects.create(
        consumable=consumable,
        user=user,
        quantity=qty,
        issued_quantity=qty,
        assigned_at=when,
        assigned_by=user,
        purpose="Generated historical issue",
    )

    create_event(
        consumable,
        ConsumableEvent.EventType.ISSUED,
        quantity=qty,
        quantity_change=-qty,
        user=user,
        when=when,
        issue=issue,
        notes=f"Issued {qty} units",
    )

    return issue


def use_consumable(issue, qty, when):
    qty = min(qty, issue.quantity)

    issue.quantity -= qty
    if issue.quantity == 0:
        issue.returned_at = when
    issue.save()

    create_event(
        issue.consumable,
        ConsumableEvent.EventType.USED,
        quantity=qty,
        quantity_change=0,
        user=issue.user,
        when=when,
        issue=issue,
        notes=f"Used {qty} units",
    )


def return_consumable(issue, qty, when):
    qty = min(qty, issue.quantity)

    issue.quantity -= qty
    if issue.quantity == 0:
        issue.returned_at = when
    issue.save()

    create_event(
        issue.consumable,
        ConsumableEvent.EventType.RETURNED,
        quantity=qty,
        quantity_change=qty,
        user=issue.user,
        when=when,
        issue=issue,
        notes=f"Returned {qty} units",
    )


def generate_consumable_timeline(consumable, users, start_time=None):
    if start_time:
        now = start_time + timedelta(days=random.randint(7, 60))
    else:
        now = timezone.now() - timedelta(days=random.randint(300, 1500))

    scenario = pick_scenario()
    user = random.choice(users)

    if consumable.quantity == 0:
        restock_qty = random.randint(15, 40)
        create_event(
            consumable,
            ConsumableEvent.EventType.RESTOCKED,
            quantity=restock_qty,
            quantity_change=restock_qty,
            user=user,
            when=now,
            notes="Initial stock",
        )
        now = next_time(now)

    if scenario == "issued_active":
        issue_consumable(consumable, user, now)

    elif scenario == "issued_used":
        issue = issue_consumable(consumable, user, now)
        if issue:
            use_consumable(issue, issue.quantity, next_time(now))

    elif scenario == "partial_used":
        issue = issue_consumable(consumable, user, now)
        if issue and issue.quantity > 1:
            use_consumable(issue, random.randint(1, issue.quantity - 1), next_time(now))

    elif scenario == "condemned":
        qty = random.randint(1, min(5, consumable.quantity))
        create_event(
            consumable,
            ConsumableEvent.EventType.CONDEMNED,
            quantity=qty,
            quantity_change=-qty,
            user=user,
            when=now,
            notes="Condemned stock",
        )

    elif scenario == "expired":
        qty = random.randint(1, min(5, consumable.quantity))
        create_event(
            consumable,
            ConsumableEvent.EventType.EXPIRED,
            quantity=qty,
            quantity_change=-qty,
            user=user,
            when=now,
            notes="Expired stock",
        )

    elif scenario == "restocked":
        qty = random.randint(10, 30)
        create_event(
            consumable,
            ConsumableEvent.EventType.RESTOCKED,
            quantity=qty,
            quantity_change=qty,
            user=user,
            when=now,
            notes="Supplier delivery",
        )

    elif scenario == "adjusted":
        delta = random.choice([-3, -2, -1, 1, 2, 3])
        create_event(
            consumable,
            ConsumableEvent.EventType.ADJUSTED,
            quantity=abs(delta),
            quantity_change=delta,
            user=user,
            when=now,
            notes="Inventory recount adjustment",
        )


def generate_multiple_timelines(consumable, users, segments):
    current_time = None

    for _ in range(segments):
        generate_consumable_timeline(consumable, users, current_time)
        current_time = get_last_event_time(consumable)
        if current_time:
            current_time += timedelta(days=random.randint(20, 120))


def bulk_fake_events(consumable, users, start_time, count):
    events = []
    current_time = start_time

    for _ in range(count):
        current_time += timedelta(minutes=random.randint(5, 240))
        events.append(
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

    ConsumableEvent.objects.bulk_create(events)


# -------------------------------
# Management command
# -------------------------------
class Command(BaseCommand):
    help = "Purge and regenerate consumable issue & event history"

    def handle(self, *args, **kwargs):
        users = list(User.objects.filter(is_active=True))
        consumables = list(Consumable.objects.all())

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

        for consumable in tqdm(
            consumables,
            desc="Processing consumables",
            unit="consumable",
        ):
            segments = random.randint(*SEGMENTS_PER_CONSUMABLE)

            generate_multiple_timelines( consumable, users, segments, )

            last_time = get_last_event_time(consumable) or timezone.now()

            bulk_fake_events(consumable, users, last_time, FAKE_EVENTS_PER_CONSUMABLE)

        self.stdout.write( self.style.SUCCESS("Consumable history generation complete 🎉") )
