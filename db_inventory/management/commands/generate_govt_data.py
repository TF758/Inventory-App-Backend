import os
import random
import django
from faker import Faker

from db_inventory.models.site import Department, Location, Room

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "inventory.settings")
django.setup()

from django.core.management import call_command
from django.core.management.base import BaseCommand
from db_inventory.factories import (
    UserFactory,
    AdminUserFactory,
    DepartmentFactory,
    UserLocationFactory,
    LocationFactory,
    EquipmentFactory,
    ComponentFactory,
    AccessoryFactory,
    ConsumableFactory,
    RoomFactory
)
from db_inventory.models import RoleAssignment
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
    PUBLIC_SERVICE_LOCATIONS
)

faker = Faker()

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

def normalize_location_name(name: str) -> str:
    return (
        name.strip()
        .replace("Saint-Lucia", "Saint Lucia")
        .replace("  ", " ")
    )

class Command(BaseCommand):
    help = 'Generate sample data for inventory database safely'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.WARNING('Clearing existing data...'))
        call_command('flush', '--no-input')
        self.stdout.write(self.style.SUCCESS('Existing data cleared.'))

        # -------------------------------
        # Departments and Locations
        # -------------------------------
        departments = []
        all_locations = []

        for ministry_name in LIST_OF_MINISTIRES:
            department, _ = Department.objects.get_or_create(
                name=ministry_name
            )
            departments.append(department)

            seen_locations = set()
            locations_list = MINISTRY_TO_LOCATIONS.get(ministry_name, [])

            for raw_name in locations_list:
                name = normalize_location_name(raw_name)
                key = (department.id, name)

                if key in seen_locations:
                    continue

                location, _ = Location.objects.get_or_create(
                    department=department,
                    name=name,
                )

                seen_locations.add(key)
                all_locations.append(location)


        # -------------------------------
        # Rooms
        # -------------------------------
        rooms = []

        for loc in all_locations:
            count = random.randint(6, 12)
            used_names = set()

            attempts = 0
            while len(used_names) < count:
                attempts += 1
                if attempts > count * 5:
                    break  # safety guard

                name = f"{faker.word().capitalize()} Room"

                if name in used_names:
                    continue

                room, _ = Room.objects.get_or_create(
                    location=loc,
                    name=name,
                )

                used_names.add(name)
                rooms.append(room)

        # -------------------------------
        # Users
        # -------------------------------
        total_users = 10000
        users = UserFactory.create_batch(total_users)
        self.stdout.write(self.style.SUCCESS(f'Created {len(users)} users.'))

        # Create 1 normal admin user
        admin_user = AdminUserFactory()
        site_admin_role = RoleAssignment.objects.create(
            user=admin_user,
            role="SITE_ADMIN",
            assigned_by=admin_user  # optional
        )
        admin_user.active_role = site_admin_role
        admin_user.save()
        self.stdout.write(self.style.SUCCESS(f'Created 1 normal admin user: {admin_user.email}'))

        # -------------------------------
        # Assign locations and roles
        # -------------------------------
        role_levels = [
            "DEPARTMENT_ADMIN", "DEPARTMENT_VIEWER",
            "LOCATION_ADMIN", "LOCATION_VIEWER",
            "ROOM_ADMIN", "ROOM_CLERK", "ROOM_VIEWER"
        ]

        for user in users:
            # Random active/inactive
            user.is_active = random.random() < 0.9
            user.save()

            # 90% chance to assign location
            loc = None
            room = None
            if random.random() < 0.9 and all_locations:
                loc = random.choice(all_locations)
                room = random.choice(list(loc.rooms.all()))
                UserLocationFactory(user=user, room=room, is_current=True)

            # 90% chance to assign role
            if random.random() < 0.9:
                role = random.choice(role_levels)
                kwargs = {}
                if role.startswith("DEPARTMENT"):
                    kwargs["department"] = loc.department if loc else random.choice(departments)
                elif role.startswith("LOCATION"):
                    kwargs["location"] = loc if loc else random.choice(all_locations)
                elif role.startswith("ROOM"):
                    kwargs["room"] = room if room else random.choice(rooms)
                RoleAssignment.objects.create(user=user, role=role, **kwargs)

        # -------------------------------
        # Equipment, Components, Accessories, Consumables
        # -------------------------------
        equipment = [EquipmentFactory(room=random.choice(rooms)) for _ in range(len(rooms)*3)]
        components = [ComponentFactory(equipment=random.choice(equipment)) for _ in range(len(equipment)*2)]
        accessories = [AccessoryFactory(room=random.choice(rooms)) for _ in range(len(rooms)*2)]
        consumables = [ConsumableFactory(room=random.choice(rooms)) for _ in range(len(rooms)*3)]

        self.stdout.write(self.style.SUCCESS('Sample data generation completed successfully.'))
