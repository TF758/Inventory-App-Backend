import random
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from tqdm import tqdm

from assignments.models.asset_assignment import (
    ConsumableEvent,
    ConsumableIssue,
)
from assets.models.assets import Consumable


User = get_user_model()

FAKE_EVENTS_PER_CONSUMABLE = 50
BATCH_SIZE = 1000
EVENT_BATCH_SIZE = 2000

SCENARIOS = {
    "issued_active": 0.30,
    "issued_used": 0.25,
    "partial_used": 0.15,
    "condemned": 0.10,
    "expired": 0.05,
    "restocked": 0.10,
    "adjusted": 0.05,
}

ISSUE_SCENARIOS = {
    "issued_active",
    "issued_used",
    "partial_used",
}

OPEN_ISSUE_SCENARIOS = {
    "issued_active",
    "partial_used",
}

SEGMENTS_PER_CONSUMABLE = (2, 4)


def next_time(current):
    return current + timedelta(days=random.randint(5, 90))


def pick_scenario():
    return random.choices(
        list(SCENARIOS.keys()),
        weights=list(SCENARIOS.values()),
    )[0]


def pick_user_without_open_issue(users, consumable_id, open_issue_pairs):
    """Return a user who does not already have an open issue for this item."""

    # Random attempts are normally enough because the local seed has many users.
    for _ in range(min(25, len(users))):
        user = random.choice(users)
        if (consumable_id, user.pk) not in open_issue_pairs:
            return user

    # Deterministic fallback guarantees correctness if random attempts collide.
    start = random.randrange(len(users))
    for offset in range(len(users)):
        user = users[(start + offset) % len(users)]
        if (consumable_id, user.pk) not in open_issue_pairs:
            return user

    return None


class Command(BaseCommand):
    help = "Purge and regenerate consumable issue & event history (bulk optimized)"

    def handle(self, *args, **kwargs):
        users = list(User.objects.filter(is_active=True))
        consumables = list(Consumable.objects.all())

        if not users:
            self.stdout.write(self.style.ERROR("No active users found; nothing generated."))
            return

        if not consumables:
            self.stdout.write(self.style.ERROR("No consumables found; nothing generated."))
            return

        event_rows = []
        issue_rows = []
        consumables_to_update = set()

        # Tracks only rows that will remain open (returned_at is NULL).
        # This mirrors unique_open_issue_per_user_consumable before bulk insertion.
        open_issue_pairs = set()

        self.stdout.write(self.style.WARNING("Purging consumable history…"))

        with transaction.atomic():
            ConsumableEvent.objects.all().delete()
            ConsumableIssue.objects.all().delete()

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
                event_user = random.choice(users)

                if consumable.quantity == 0:
                    restock_qty = random.randint(15, 40)
                    consumable.quantity += restock_qty
                    consumables_to_update.add(consumable)

                    event_rows.append(
                        ConsumableEvent(
                            consumable=consumable,
                            user=event_user,
                            reported_by=event_user,
                            event_type=ConsumableEvent.EventType.RESTOCKED,
                            quantity=restock_qty,
                            quantity_change=restock_qty,
                            occurred_at=current_time,
                            notes="Initial stock",
                        )
                    )
                    current_time = next_time(current_time)

                if scenario in ISSUE_SCENARIOS:
                    if scenario == "partial_used":
                        if consumable.quantity < 2:
                            current_time = next_time(current_time)
                            continue
                        issued_quantity = min(
                            random.randint(2, 5),
                            consumable.quantity,
                        )
                    else:
                        issued_quantity = min(
                            random.randint(1, 5),
                            consumable.quantity,
                        )

                    if issued_quantity <= 0:
                        current_time = next_time(current_time)
                        continue

                    if scenario in OPEN_ISSUE_SCENARIOS:
                        user = pick_user_without_open_issue(
                            users,
                            consumable.pk,
                            open_issue_pairs,
                        )
                        if user is None:
                            # Every active user already has an open issue for this item.
                            current_time = next_time(current_time)
                            continue
                    else:
                        user = event_user

                    issued_at = current_time
                    remaining_quantity = issued_quantity
                    closed_at = None
                    used_quantity = 0

                    if scenario == "issued_used":
                        used_quantity = issued_quantity
                        remaining_quantity = 0
                        closed_at = next_time(issued_at)
                    elif scenario == "partial_used":
                        used_quantity = random.randint(1, issued_quantity - 1)
                        remaining_quantity = issued_quantity - used_quantity

                    issue = ConsumableIssue(
                        consumable=consumable,
                        user=user,
                        quantity=remaining_quantity,
                        issued_quantity=issued_quantity,
                        assigned_at=issued_at,
                        assigned_by=user,
                        returned_at=closed_at,
                        purpose="Generated historical issue",
                    )
                    issue_rows.append(issue)

                    if scenario in OPEN_ISSUE_SCENARIOS:
                        open_issue_pairs.add((consumable.pk, user.pk))

                    # Stock leaves inventory when it is issued. Later use events do not
                    # reduce inventory again because those units are already off shelf.
                    consumable.quantity -= issued_quantity
                    consumables_to_update.add(consumable)

                    event_rows.append(
                        ConsumableEvent(
                            consumable=consumable,
                            issue=issue,
                            user=user,
                            reported_by=user,
                            event_type=ConsumableEvent.EventType.ISSUED,
                            quantity=issued_quantity,
                            quantity_change=-issued_quantity,
                            occurred_at=issued_at,
                            notes=f"Issued {issued_quantity} units",
                        )
                    )

                    if scenario in {"issued_used", "partial_used"}:
                        used_at = closed_at or next_time(issued_at)
                        event_rows.append(
                            ConsumableEvent(
                                consumable=consumable,
                                issue=issue,
                                user=user,
                                reported_by=user,
                                event_type=ConsumableEvent.EventType.USED,
                                quantity=used_quantity,
                                quantity_change=0,
                                occurred_at=used_at,
                                notes=f"Used {used_quantity} units",
                            )
                        )
                        current_time = used_at

                elif scenario == "condemned":
                    quantity = min(random.randint(1, 5), consumable.quantity)
                    if quantity > 0:
                        consumable.quantity -= quantity
                        consumables_to_update.add(consumable)
                        event_rows.append(
                            ConsumableEvent(
                                consumable=consumable,
                                user=event_user,
                                reported_by=event_user,
                                event_type=ConsumableEvent.EventType.CONDEMNED,
                                quantity=quantity,
                                quantity_change=-quantity,
                                occurred_at=current_time,
                                notes="Condemned stock",
                            )
                        )

                elif scenario == "expired":
                    quantity = min(random.randint(1, 5), consumable.quantity)
                    if quantity > 0:
                        consumable.quantity -= quantity
                        consumables_to_update.add(consumable)
                        event_rows.append(
                            ConsumableEvent(
                                consumable=consumable,
                                user=event_user,
                                reported_by=event_user,
                                event_type=ConsumableEvent.EventType.EXPIRED,
                                quantity=quantity,
                                quantity_change=-quantity,
                                occurred_at=current_time,
                                notes="Expired stock",
                            )
                        )

                elif scenario == "restocked":
                    quantity = random.randint(10, 30)
                    consumable.quantity += quantity
                    consumables_to_update.add(consumable)
                    event_rows.append(
                        ConsumableEvent(
                            consumable=consumable,
                            user=event_user,
                            reported_by=event_user,
                            event_type=ConsumableEvent.EventType.RESTOCKED,
                            quantity=quantity,
                            quantity_change=quantity,
                            occurred_at=current_time,
                            notes="Supplier delivery",
                        )
                    )

                elif scenario == "adjusted":
                    requested_delta = random.choice([-3, -2, -1, 1, 2, 3])
                    previous_quantity = consumable.quantity
                    consumable.quantity = max(0, previous_quantity + requested_delta)
                    actual_delta = consumable.quantity - previous_quantity
                    consumables_to_update.add(consumable)

                    event_rows.append(
                        ConsumableEvent(
                            consumable=consumable,
                            user=event_user,
                            reported_by=event_user,
                            event_type=ConsumableEvent.EventType.ADJUSTED,
                            quantity=abs(actual_delta),
                            quantity_change=actual_delta,
                            occurred_at=current_time,
                            notes="Inventory recount adjustment",
                        )
                    )

                current_time = next_time(current_time)

            # Extra display-only activity. These rows deliberately do not create or
            # modify issues, so they cannot violate issue constraints.
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

        self.stdout.write(self.style.MIGRATE_HEADING("Writing history to database…"))

        with transaction.atomic():
            if issue_rows:
                ConsumableIssue.objects.bulk_create(
                    issue_rows,
                    batch_size=BATCH_SIZE,
                )

            if event_rows:
                ConsumableEvent.objects.bulk_create(
                    event_rows,
                    batch_size=EVENT_BATCH_SIZE,
                )

            if consumables_to_update:
                Consumable.objects.bulk_update(
                    list(consumables_to_update),
                    ["quantity"],
                    batch_size=BATCH_SIZE,
                )

        open_issue_count = sum(1 for issue in issue_rows if issue.returned_at is None)
        closed_issue_count = len(issue_rows) - open_issue_count

        self.stdout.write(
            self.style.SUCCESS(
                "Consumable history generation complete 🎉\n"
                f"- Issues: {len(issue_rows):,} "
                f"({open_issue_count:,} open, {closed_issue_count:,} closed)\n"
                f"- Events: {len(event_rows):,}"
            )
        )