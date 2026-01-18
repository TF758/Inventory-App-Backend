import os
import random
import django
from datetime import timedelta
from django.utils import timezone

from db_inventory.models.asset_assignment import ConsumableEvent, ConsumableIssue
from db_inventory.models.assets import Consumable

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "inventory.settings")
django.setup()

from django.core.management.base import BaseCommand

from db_inventory.models.users import User


SCENARIOS = {
    "issued_active": 0.30,       # issued, still being used
    "issued_used": 0.25,         # issued, fully used
    "partial_used": 0.15,        # issued, partially used
    "condemned": 0.10,           # stock condemned
    "expired": 0.05,             # expired stock
    "restocked": 0.10,           # new stock
    "adjusted": 0.05,            # inventory adjustment
}


def next_time(current):
    return current + timedelta(days=random.randint(5, 90))


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


def generate_consumable_timeline(consumable, users):
    now = timezone.now() - timedelta(days=random.randint(180, 1200))
    scenario = random.choices(
        list(SCENARIOS.keys()),
        weights=list(SCENARIOS.values()),
    )[0]

    user = random.choice(users)

    # Ensure starting stock
    if consumable.quantity == 0:
        restock_qty = random.randint(10, 30)
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
            now = next_time(now)
            use_consumable(issue, issue.quantity, now)

    elif scenario == "partial_used":
        issue = issue_consumable(consumable, user, now)
        if issue and issue.quantity > 1:
            now = next_time(now)
            use_consumable(issue, random.randint(1, issue.quantity - 1), now)

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
        qty = random.randint(10, 25)
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


class Command(BaseCommand):
    help = "Generate historical consumable issues and events"

    def handle(self, *args, **kwargs):
        consumables = Consumable.objects.all()
        users = list(User.objects.filter(is_active=True))

        self.stdout.write(
            f"Generating history for {consumables.count()} consumables"
        )

        for consumable in consumables:
            if consumable.events.exists():
                continue

            generate_consumable_timeline(consumable, users)

        self.stdout.write(
            self.style.SUCCESS("Consumable history generation complete")
        )
