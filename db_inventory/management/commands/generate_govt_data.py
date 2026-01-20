import os
import random
import django
from faker import Faker
from tqdm import tqdm  # progress bars
from django.contrib.auth.hashers import make_password
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "inventory.settings")
django.setup()

from django.core.management.base import BaseCommand
from django.core.management import call_command

from db_inventory.models.site import Department, Location, Room, UserLocation
from db_inventory.models.users import User
from db_inventory.models import RoleAssignment

from db_inventory.factories import (
    UserFactory,
    AdminUserFactory,
    EquipmentFactory,
    ComponentFactory,
    AccessoryFactory,
    ConsumableFactory,
)

from ...ministry_data import (
    LIST_OF_MINISTIRES,
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
)

faker = Faker()

TOTAL_USERS = 10_000
BATCH_SIZE = 1_000


ROLE_LEVELS = [
    "DEPARTMENT_ADMIN", "DEPARTMENT_VIEWER",
    "LOCATION_ADMIN", "LOCATION_VIEWER",
    "ROOM_ADMIN", "ROOM_CLERK", "ROOM_VIEWER",
]

MINISTRY_TO_LOCATIONS = {
    "Ministry of Finance, Economic Development and Youth Economy": FINANCE_LOCATIONS,
    "Ministry of Tourism, Investment, Creative Industries, Culture and Information": TOURISM_LOCATIONS,
    "Ministry of Health, Wellness and Elderly Affairs": HEALTH_LOCATIONS,
    "Ministry of Education, Sustainable Development, Innovation, Science, Technology and Vocational Training": [],
    "Ministry of External Affairs, International Trade, Civil Aviation and Diaspora Affairs": EXTERNAL_AFFAIRS_LOCATIONS,
    "Ministry of Infrastructure, Ports, Transport, Physical Development and Urban Renewal": TRANSPORT_LOCATIONS,
    "Ministry of Commerce, Manufacturing, Business Development, Cooperatives and Consumer Affairs": COMMERCE_LOCATIONS,
    "Ministry of Equity, Social Justice and Empowerment": EQUITY_LOCATIONS,
    "Ministry of the Public Service, Home Affairs, Labour and Gender Affairs": PUBLIC_SERVICE_LOCATIONS,
    "Ministry of Youth Development and Sports": YOUTH_AND_SPORTS_LOCATIONS,
    "Ministry of Agriculture, Fisheries, Food Security and Rural Development": AGRICULTURE_LOCATIONS,
    "Ministry of Housing and Local Government": HOUSING_LOCATIONS,
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

        for ministry in tqdm(LIST_OF_MINISTIRES, desc="Ministries"):
            dept = Department.objects.create(name=ministry)
            departments.append(dept)

            seen_locations = set()

            for raw in MINISTRY_TO_LOCATIONS.get(ministry, []):
                name = normalize(raw)
                if name in seen_locations:
                    continue
                seen_locations.add(name)

                loc = Location.objects.create(department=dept, name=name)
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
                    rooms.append(Room.objects.create(location=loc, name=room_name))

        self.stdout.write(self.style.SUCCESS("Sites created."))


        self.stdout.write(
    self.style.MIGRATE_HEADING(
        f"Creating {TOTAL_USERS:,} users (fast mode)"
    )
)

        users = []
        password_hash = make_password("password")

        for i in tqdm(
            range(TOTAL_USERS),
            desc="Preparing users",
        ):
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

        for start in tqdm(
            range(0, TOTAL_USERS, BATCH_SIZE),
            desc="Saving users to database",
        ):
            User.objects.bulk_create(
                users[start:start + BATCH_SIZE],
                batch_size=BATCH_SIZE,
            )


        for u in tqdm(users, desc="Activating users"):
            u.is_active = random.random() < 0.9

        User.objects.bulk_update(users, ["is_active"])

        if User.objects.filter(public_id__isnull=True).exists():
            raise RuntimeError("Some users missing public_id")

        self.stdout.write(self.style.SUCCESS(f"{len(users):,} users created."))


        self.stdout.write(self.style.MIGRATE_HEADING("Creating admin user"))

        admin = AdminUserFactory(email="admin@gmail.com")

        admin_role = RoleAssignment.objects.create(
            user=admin,
            role="SITE_ADMIN",
            assigned_by=admin,
        )
        admin.active_role = admin_role
        admin.save(update_fields=["active_role"])

        self.stdout.write(self.style.SUCCESS("Admin user created."))


        self.stdout.write(
            self.style.MIGRATE_HEADING("Assigning users to locations")
        )

        user_locations = []

        for user in tqdm(users, desc="Assigning locations"):
            # ~90% of users get a location
            if random.random() < 0.9:
                room = random.choice(rooms)
                user_locations.append(
                    UserLocation(
                        user=user,
                        room=room,
                        is_current=True,
                    )
                )

        # bulk insert
        UserLocation.objects.bulk_create(
            user_locations,
            batch_size=BATCH_SIZE,
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"{len(user_locations):,} users assigned to rooms"
            )
        )


        self.stdout.write(self.style.MIGRATE_HEADING("Assigning roles"))

        for user in tqdm(users, desc="Assigning roles"):
            roles = []
            used = set()

            for _ in range(pick_role_count()):
                role = random.choice(ROLE_LEVELS)

                try:
                    if role.startswith("DEPARTMENT"):
                        dept = random.choice(departments)
                        key = ("D", dept.id)
                        if key in used:
                            continue
                        used.add(key)
                        roles.append(RoleAssignment.objects.create(
                            user=user, role=role, department=dept
                        ))

                    elif role.startswith("LOCATION"):
                        loc = random.choice(locations)
                        key = ("L", loc.id)
                        if key in used:
                            continue
                        used.add(key)
                        roles.append(RoleAssignment.objects.create(
                            user=user, role=role, location=loc
                        ))

                    elif role.startswith("ROOM"):
                        room = random.choice(rooms)
                        key = ("R", room.id)
                        if key in used:
                            continue
                        used.add(key)
                        roles.append(RoleAssignment.objects.create(
                            user=user, role=role, room=room
                        ))
                except Exception:
                    continue

            if roles and random.random() > 0.15:
                user.active_role = random.choice(roles)
                user.save(update_fields=["active_role"])

        self.stdout.write(self.style.SUCCESS("Roles assigned."))

        self.stdout.write(self.style.MIGRATE_HEADING("Creating assets"))

        equipment = [
            EquipmentFactory(room=random.choice(rooms))
            for _ in tqdm(range(len(rooms) * 3), desc="Equipment")
        ]

        for eq in tqdm(equipment, desc="Components"):
            ComponentFactory.create_batch(2, equipment=eq)

        AccessoryFactory.create_batch(len(rooms) * 2, room=random.choice(rooms))
        ConsumableFactory.create_batch(len(rooms) * 3, room=random.choice(rooms))

        self.stdout.write( self.style.SUCCESS("Assets generated successfully 🎉") )
