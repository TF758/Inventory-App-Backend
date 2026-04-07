import random
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from tqdm import tqdm

from db_inventory.models.asset_assignment import (
    EquipmentAssignment,
    EquipmentEvent,
)
from db_inventory.models.assets import Equipment
from db_inventory.models.users import User


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


def pick_scenario():
    return random.choices(
        list(SCENARIOS.keys()),
        weights=list(SCENARIOS.values()),
    )[0]


def next_time(current):
    return current + timedelta(days=random.randint(10, 180))
class Command(BaseCommand):
    help = "Purge and regenerate equipment assignment & event history (bulk optimized)"

    def handle(self, *args, **kwargs):

        users = list(User.objects.filter(is_active=True))
        equipments = list(Equipment.objects.all())

        event_rows = []
        assignment_rows = []
        equipment_updates = set()

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

        for equipment in tqdm(equipments, desc="Processing equipment"):

            current_time = timezone.now() - timedelta(
                days=random.randint(500, 1800)
            )

            segments = random.randint(*SEGMENTS_PER_EQUIPMENT)

            assignment = None
            assigned_user = None

            for _ in range(segments):

                scenario = pick_scenario()
                user = random.choice(users)

                # -------------------------
                # ASSIGNED ACTIVE
                # -------------------------
                if scenario == "assigned_active":

                    if assignment is None:
                        assignment = EquipmentAssignment(
                            equipment=equipment,
                            user=user,
                            assigned_by=user,
                            assigned_at=current_time,
                        )
                        assignment_rows.append(assignment)

                    assigned_user = user

                    event_rows.append(
                        EquipmentEvent(
                            equipment=equipment,
                            user=user,
                            reported_by=user,
                            event_type="assigned",
                            occurred_at=current_time,
                        )
                    )

                    equipment.status = "ok"
                    equipment_updates.add(equipment)

                # -------------------------
                # ASSIGNED THEN RETURNED
                # -------------------------
                elif scenario == "assigned_returned":

                    if assignment is None:
                        assignment = EquipmentAssignment(
                            equipment=equipment,
                            user=user,
                            assigned_by=user,
                            assigned_at=current_time,
                        )
                        assignment_rows.append(assignment)

                    assigned_user = user

                    event_rows.append(
                        EquipmentEvent(
                            equipment=equipment,
                            user=user,
                            reported_by=user,
                            event_type="assigned",
                            occurred_at=current_time,
                        )
                    )

                    current_time = next_time(current_time)

                    event_rows.append(
                        EquipmentEvent(
                            equipment=equipment,
                            user=user,
                            reported_by=user,
                            event_type="returned",
                            occurred_at=current_time,
                        )
                    )

                    assigned_user = None

                # -------------------------
                # REASSIGNED
                # -------------------------
                elif scenario == "reassigned":

                    if assignment is None:
                        assignment = EquipmentAssignment(
                            equipment=equipment,
                            user=user,
                            assigned_by=user,
                            assigned_at=current_time,
                        )
                        assignment_rows.append(assignment)

                    assigned_user = user

                    event_rows.append(
                        EquipmentEvent(
                            equipment=equipment,
                            user=user,
                            reported_by=user,
                            event_type="assigned",
                            occurred_at=current_time,
                        )
                    )

                    current_time = next_time(current_time)

                    new_user = random.choice(users)

                    event_rows.append(
                        EquipmentEvent(
                            equipment=equipment,
                            user=user,
                            reported_by=user,
                            event_type="returned",
                            occurred_at=current_time,
                        )
                    )

                    event_rows.append(
                        EquipmentEvent(
                            equipment=equipment,
                            user=new_user,
                            reported_by=new_user,
                            event_type="assigned",
                            occurred_at=current_time,
                        )
                    )

                    assigned_user = new_user

                # -------------------------
                # DAMAGED / REPAIRED
                # -------------------------
                elif scenario == "damaged_repaired":

                    event_rows.append(
                        EquipmentEvent(
                            equipment=equipment,
                            user=user,
                            reported_by=user,
                            event_type="damaged",
                            occurred_at=current_time,
                        )
                    )

                    equipment.status = "damaged"
                    equipment_updates.add(equipment)

                    current_time = next_time(current_time)

                    event_rows.append(
                        EquipmentEvent(
                            equipment=equipment,
                            user=user,
                            reported_by=user,
                            event_type="repaired",
                            occurred_at=current_time,
                        )
                    )

                    equipment.status = "ok"
                    equipment_updates.add(equipment)

                # -------------------------
                # LOST / RETIRED
                # -------------------------
                elif scenario == "lost_or_retired":

                    event_type = random.choice(["lost", "retired"])

                    event_rows.append(
                        EquipmentEvent(
                            equipment=equipment,
                            user=user,
                            reported_by=user,
                            event_type=event_type,
                            occurred_at=current_time,
                        )
                    )

                    equipment.status = EVENT_TO_STATUS[event_type]
                    equipment_updates.add(equipment)

                current_time = next_time(current_time)

            # -------------------------
            # SYNTHETIC EVENTS
            # -------------------------

            for _ in range(FAKE_EVENTS_PER_EQUIPMENT):

                current_time += timedelta(minutes=random.randint(5, 240))

                event_rows.append(
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

        self.stdout.write(self.style.MIGRATE_HEADING("Writing history to database…"))

        with transaction.atomic():

            if assignment_rows:
                EquipmentAssignment.objects.bulk_create(
                    assignment_rows,
                    batch_size=1000,
                )

            if event_rows:
                EquipmentEvent.objects.bulk_create(
                    event_rows,
                    batch_size=2000,
                )

            if equipment_updates:
                Equipment.objects.bulk_update(
                    list(equipment_updates),
                    ["status"],
                    batch_size=1000,
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"Equipment history generation complete 🎉 "
                f"({len(event_rows):,} events)"
            )
        )