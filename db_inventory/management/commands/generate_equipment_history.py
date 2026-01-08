import os
import random
import django
from faker import Faker
from datetime import timedelta
import random
from django.utils import timezone
from db_inventory.models.asset_assignment import EquipmentAssignment, EquipmentEvent
from db_inventory.models.assets import Equipment
from db_inventory.models.users import User

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "inventory.settings")
django.setup()


from django.core.management import call_command
from django.core.management.base import BaseCommand

SCENARIOS = {
    "assigned_active": 0.30,
    "assigned_returned": 0.25,
    "reassigned": 0.20,
    "damaged_repaired": 0.15,
    "lost_or_retired": 0.10,
}
EVENT_TO_STATUS = {
    "assigned": "ok",
    "returned": "ok",
    "damaged": "damaged",
    "repaired": "ok",
    "lost": "lost",
    "retired": "retired",
    "under_repair": "under_repair",
}


def next_time(current):
    return current + timedelta(days=random.randint(5, 180))

def pick_scenario():
    scenarios = list(SCENARIOS.keys())
    weights = list(SCENARIOS.values())
    return random.choices(scenarios, weights=weights)[0]

def create_event(equipment, event_type, user, when):
    EquipmentEvent.objects.create(equipment=equipment,user=user,reported_by=user,event_type=event_type,occurred_at=when,)

    equipment.status = EVENT_TO_STATUS[event_type]
    equipment.save(update_fields=["status"])
def assign_equipment(equipment, user, when):

    """
    Mirrors AssignEquipmentView
    """
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
    """
    Mirrors UnassignEquipmentView
    """
    if not equipment.is_assigned:
        return

    assignment = equipment.active_assignment
    assignment.returned_at = when
    assignment.save(update_fields=["returned_at"])

    create_event(equipment, "returned", assignment.user, when)


def reassign_equipment(equipment, new_user, when):
    """
    Mirrors ReassignEquipmentView
    """
    if not equipment.is_assigned:
        assign_equipment(equipment, new_user, when)
        return

    assignment = equipment.active_assignment
    old_user = assignment.user

    # Returned from old user
    create_event(equipment, "returned", old_user, when)

    # Mutate assignment
    assignment.user = new_user
    assignment.assigned_by = new_user
    assignment.assigned_at = when
    assignment.returned_at = None
    assignment.save()

    create_event(equipment, "assigned", new_user, when)


def generate_timeline(equipment, users):
    now = timezone.now() - timedelta(days=random.randint(365, 1500))
    scenario = pick_scenario()
    user = random.choice(users)

    if scenario == "assigned_active":
        assign_equipment(equipment, user, now)

    elif scenario == "assigned_returned":
        assign_equipment(equipment, user, now)
        now = next_time(now)
        unassign_equipment(equipment, now)

    elif scenario == "reassigned":
        assign_equipment(equipment, user, now)
        now = next_time(now)
        reassign_equipment(equipment, random.choice(users), now)

    elif scenario == "damaged_repaired":
        assign_equipment(equipment, user, now)
        now = next_time(now)
        create_event(equipment, "damaged", user, now)
        now = next_time(now)
        create_event(equipment, "repaired", user, now)

    elif scenario == "lost_or_retired":
        assign_equipment(equipment, user, now)
        now = next_time(now)
        create_event(
            equipment,
            random.choice(["lost", "retired"]),
            user,
            now,
        )

class Command(BaseCommand):
    help = "Generate historical equipment assignments and events"

    def handle(self, *args, **kwargs):
        equipments = Equipment.objects.all()
        users = list(User.objects.filter(is_active=True))

        self.stdout.write(
            f"Generating history for {equipments.count()} equipment items"
        )

        for equipment in equipments:
            # Skip equipment that already has history
            if EquipmentEvent.objects.filter(equipment=equipment).exists():
                continue

            generate_timeline(equipment, users)

        self.stdout.write(
            self.style.SUCCESS("Equipment history generation complete")
        )