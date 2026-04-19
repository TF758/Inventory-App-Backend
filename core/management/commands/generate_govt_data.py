import itertools
import os
import random
import django
from faker import Faker
from tqdm import tqdm  # progress bars
from django.contrib.auth.hashers import make_password

from assets.models.assets import Accessory, Component, Consumable, Equipment

from core.tests.test_audit_logs import User
from assets.asset_factories import AccessoryFactory, ComponentFactory, ConsumableFactory, EquipmentFactory
from sites.models.sites import Department, Location, Room, UserPlacement
from users.factories.user_factories import AdminUserFactory
from users.models.roles import RoleAssignment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "inventory.settings")
django.setup()

from django.core.management.base import BaseCommand
from django.core.management import call_command


from ...ministry_data import (
    LIST_OF_MINISTRIES,

    FINANCE_LOCATIONS,
    HEALTH_LOCATIONS,
    EQUITY_LOCATIONS,
    TRANSPORT_LOCATIONS,
    AGRICULTURE_LOCATIONS,
    EXTERNAL_AFFAIRS_LOCATIONS,
    YOUTH_AND_SPORTS_LOCATIONS,
    HOUSING_LOCATIONS,
    TOURISM_LOCATIONS,
    COMMERCE_LOCATIONS,
    PUBLIC_SERVICE_LOCATIONS,
    HOME_AFFAIRS_LOCATIONS,
    JUSTICE_LOCATIONS,
    EDUCATION_LOCATIONS
)

faker = Faker()

TOTAL_USERS = 10_000
BATCH_SIZE = 1_000


ROLE_LEVELS = [
    "DEPARTMENT_ADMIN", "DEPARTMENT_VIEWER",
    "LOCATION_ADMIN", "LOCATION_VIEWER",
    "ROOM_ADMIN", "ROOM_CLERK", "ROOM_VIEWER",
]

def merge_locations(*lists):
    seen = set()
    result = []
    for lst in lists:
        for item in lst:
            if item not in seen:
                seen.add(item)
                result.append(item)
    return result

MINISTRY_TO_LOCATIONS = {

    # Finance + Justice (correct portfolio grouping)
    "Finance, Justice, National Security, Constituency Development and People Empowerment":
        merge_locations(FINANCE_LOCATIONS, JUSTICE_LOCATIONS),

    "Tourism, Commerce, Investment, Creative Industries, Culture and Heritage":
        merge_locations(TOURISM_LOCATIONS, COMMERCE_LOCATIONS),

    "External Affairs, International Trade, Civil Aviation and Diaspora Affairs":
        EXTERNAL_AFFAIRS_LOCATIONS,

    "Health, Wellness and Nutrition":
        HEALTH_LOCATIONS,

    "Infrastructure, Ports Services and Energy":
        TRANSPORT_LOCATIONS,

    "Agriculture, Fisheries, Food Security and Climate Change":
        AGRICULTURE_LOCATIONS,

    "Equity, Labour, Gender and Elderly Affairs, Social Justice and Consumer Welfare":
        EQUITY_LOCATIONS,

    "Education, Youth Development, Sports and Digital Transformation":
        merge_locations(EDUCATION_LOCATIONS, YOUTH_AND_SPORTS_LOCATIONS),

    "Economic Development and the Youth Economy":
        merge_locations(COMMERCE_LOCATIONS, YOUTH_AND_SPORTS_LOCATIONS),

    "Home Affairs, Crime Prevention, Conflict Resolution and Persons with Disabilities":
        HOME_AFFAIRS_LOCATIONS,

    "Physical Development and Public Utilities":
        merge_locations(TRANSPORT_LOCATIONS, HOUSING_LOCATIONS),

    "Housing, Local Government and Urban Renewal":
        HOUSING_LOCATIONS,

    "Public Service, Transport, Information and Utilities Regulations":
        merge_locations(PUBLIC_SERVICE_LOCATIONS, TRANSPORT_LOCATIONS),
}

def normalize(name: str) -> str:
    return name.strip().replace("Saint-Lucia", "Saint Lucia").replace("  ", " ")


def pick_role_count():
    r = random.random()
    if r < 0.55:
        return 1
    elif r < 0.80:
        return random.randint(2, 3)
    elif r < 0.90:
        return 0
    else:
        return random.randint(3, 5)



class Command(BaseCommand):
    help = "Purge and reseed core data (users, roles, sites, assets)"

    def handle(self, *args, **kwargs):

        self.stdout.write(self.style.WARNING("Flushing database…"))
        call_command("flush", "--no-input")

        # -------------------------------
        # Departments / Locations / Rooms
        # -------------------------------

        self.stdout.write(self.style.MIGRATE_HEADING("Creating site hierarchy"))

        departments, locations, rooms = [], [], []

        for ministry in tqdm(LIST_OF_MINISTRIES, desc="Ministries"):

            dept = Department.objects.create(name=ministry)
            departments.append(dept)

            seen_locations = set()
            locations_list = MINISTRY_TO_LOCATIONS.get(ministry)

            if not locations_list:
                continue

            for raw in locations_list:

                name = normalize(raw)

                if name in seen_locations:
                    continue

                seen_locations.add(name)

                loc = Location.objects.create(
                    department=dept,
                    name=name
                )

                locations.append(loc)

                seen_rooms = set()
                room_count = random.randint(6, 12)
                attempts = 0

                while len(seen_rooms) < room_count:

                    attempts += 1

                    if attempts > room_count * 5:
                        break

                    room_name = f"{faker.word().capitalize()} Room"

                    if room_name in seen_rooms:
                        continue

                    seen_rooms.add(room_name)

                    rooms.append(
                        Room.objects.create(
                            location=loc,
                            name=room_name
                        )
                    )

        self.stdout.write(self.style.SUCCESS("Sites created."))

        # -------------------------------
        # Build lookup maps
        # -------------------------------

        locations_by_department = {}
        rooms_by_location = {}

        for loc in locations:
            locations_by_department.setdefault(loc.department_id, []).append(loc)

        for room in rooms:
            rooms_by_location.setdefault(room.location_id, []).append(room)

        # -------------------------------
        # Users
        # -------------------------------

        self.stdout.write(
            self.style.MIGRATE_HEADING(
                f"Creating {TOTAL_USERS:,} users"
            )
        )

        users = []
        password_hash = make_password("password")

        for i in tqdm(range(TOTAL_USERS), desc="Preparing users"):

            users.append(
                User(
                    public_id=f"USR{i+1:07d}",
                    email=f"user{i+1}@example.com",
                    password=password_hash,
                    fname=faker.first_name(),
                    lname=faker.last_name(),
                    job_title=faker.job()[:50],
                    is_active=random.random() < 0.9,
                    is_system_user=True,
                )
            )

        for start in tqdm(range(0, TOTAL_USERS, BATCH_SIZE), desc="Saving users"):
            User.objects.bulk_create(
                users[start:start + BATCH_SIZE],
                batch_size=BATCH_SIZE
            )

        self.stdout.write(self.style.SUCCESS(f"{len(users):,} users created."))

        # -------------------------------
        # Admin
        # -------------------------------

        admin = AdminUserFactory(email="admin@gmail.com")

        admin_role = RoleAssignment.objects.create(
            user=admin,
            role="SITE_ADMIN",
            assigned_by=admin,
        )

        admin.active_role = admin_role
        admin.save(update_fields=["active_role"])

        # -------------------------------
        # Assign users to rooms
        # -------------------------------

        self.stdout.write(self.style.MIGRATE_HEADING("Assigning users to locations"))

        user_placements = []

        users_iter = iter(users)

        for room in rooms:

            try:
                user = next(users_iter)
            except StopIteration:
                break

            user_placements.append(
                UserPlacement(
                    user=user,
                    room=room,
                    is_current=True
                )
            )

        remaining_users = users[len(user_placements):]

        for user in tqdm(remaining_users):

            if random.random() < 0.98:

                dept = random.choice(departments)
                dept_locations = locations_by_department.get(dept.id)

                if not dept_locations:
                    continue

                loc = random.choice(dept_locations)
                loc_rooms = rooms_by_location.get(loc.id)

                if not loc_rooms:
                    continue

                room = random.choice(loc_rooms)

                user_placements.append(
                    UserPlacement(
                        user=user,
                        room=room,
                        is_current=True
                    )
                )

        UserPlacement.objects.bulk_create(user_placements, batch_size=BATCH_SIZE)

        placement_map = {p.user_id: p for p in user_placements}

        # -------------------------------
        # Assign roles
        # -------------------------------

        self.stdout.write(self.style.MIGRATE_HEADING("Assigning roles"))

        role_rows = []
        roles_by_user = {}

        for user in tqdm(users):

            roles = []
            used = set()

            user_loc = placement_map.get(user.id)

            if not user_loc:
                continue

            room = user_loc.room
            loc = room.location
            dept = loc.department

            for _ in range(pick_role_count()):

                role = random.choice(ROLE_LEVELS)

                try:

                    if role.startswith("DEPARTMENT"):

                        key = ("D", dept.id)

                        if key in used:
                            continue

                        used.add(key)

                        role_obj = RoleAssignment(
                            user=user,
                            role=role,
                            department=dept,
                        )

                    elif role.startswith("LOCATION"):

                        key = ("L", loc.id)

                        if key in used:
                            continue

                        used.add(key)

                        role_obj = RoleAssignment(
                            user=user,
                            role=role,
                            location=loc,
                        )

                    elif role.startswith("ROOM"):

                        key = ("R", room.id)

                        if key in used:
                            continue

                        used.add(key)

                        role_obj = RoleAssignment(
                            user=user,
                            role=role,
                            room=room,
                        )

                    else:
                        continue

                    role_rows.append(role_obj)
                    roles.append(role_obj)

                except Exception:
                    continue

            if roles and random.random() > 0.15:
                roles_by_user[user.id] = roles

        # -------------------------------
        # Bulk create roles
        # -------------------------------

        RoleAssignment.objects.bulk_create(role_rows, batch_size=BATCH_SIZE)

        # -------------------------------
        # Assign active roles
        # -------------------------------

        for user in users:

            roles = roles_by_user.get(user.id)

            if roles:
                user.active_role = random.choice(roles)

        User.objects.bulk_update(users, ["active_role"], batch_size=BATCH_SIZE)

        # -------------------------------
        # Equipment
        # -------------------------------

        self.stdout.write(self.style.MIGRATE_HEADING("Creating equipment"))

        equipment = []

        for room in rooms:
            equipment.append(EquipmentFactory.build(room=room))

        for _ in tqdm(range(len(rooms) * 2), desc="Equipment"):
            equipment.append(EquipmentFactory.build(room=random.choice(rooms)))

        Equipment.objects.bulk_create(equipment, batch_size=BATCH_SIZE)

        equipment = list(Equipment.objects.all())

        # -------------------------------
        # Components
        # -------------------------------

        components = []

        for eq in tqdm(equipment, desc="Preparing components"):
            components.extend(ComponentFactory.build_batch(2, equipment=eq))

        Component.objects.bulk_create(components, batch_size=BATCH_SIZE)

        # -------------------------------
        # Accessories
        # -------------------------------

        accessories = []

        for room in tqdm(
            itertools.islice(itertools.cycle(rooms), len(rooms) * 2),
            desc="Accessories"
        ):
            accessories.append(AccessoryFactory.build(room=room))

        Accessory.objects.bulk_create(accessories, batch_size=BATCH_SIZE)

        # -------------------------------
        # Consumables
        # -------------------------------

        consumables = []

        for room in tqdm(
            itertools.islice(itertools.cycle(rooms), len(rooms) * 3),
            desc="Consumables"
        ):
            consumables.append(ConsumableFactory.build(room=room))

        Consumable.objects.bulk_create(consumables, batch_size=BATCH_SIZE)

        self.stdout.write(self.style.SUCCESS("Assets generated successfully 🎉"))