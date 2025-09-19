import os
import random
import django

# Set the default Django settings module
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "inventory.settings")

# Setup Django
django.setup()

from django.core.management import call_command

from django.core.management.base import BaseCommand
from inventory.db_inventory.factories import (
    UserFactory, AdminUserFactory,
    DepartmentFactory,
    UserLocationFactory,
    LocationFactory,
    EquipmentFactory,
    ComponentFactory,
    AccessoryFactory,
    ConsumableFactory,
    RoomFactory
)


class Command(BaseCommand):
    help = 'Generate sample data for the inventory database'

    def handle(self, *args, **kwargs):

        # Clear existing data

        self.stdout.write(self.style.WARNING('Clearing existing data...'))
        call_command('flush', '--no-input')

        self.stdout.write(self.style.SUCCESS('Existing data cleared.'))

        self.stdout.write(self.style.SUCCESS('Generating sample data...'))
        
         # Users
        user_count = random.randint(300, 500)
        users = UserFactory.create_batch(user_count)
        self.stdout.write(self.style.SUCCESS(f'Created {len(users)} users.'))

        admin_user = AdminUserFactory.create()
        self.stdout.write(self.style.SUCCESS(f'Created admin user: {admin_user.email}'))

        # Departments (fixed 11)
        departments = DepartmentFactory.create_batch(11)
        self.stdout.write(self.style.SUCCESS(f'Created {len(departments)} departments.'))

        # Locations per department (10–20)
        locations = []
        for dept in departments:
            count = random.randint(10, 20)
            dept_locations = LocationFactory.create_batch(count, department=dept)
            locations.extend(dept_locations)
        self.stdout.write(self.style.SUCCESS(f'Created {len(locations)} locations.'))

        # Rooms per location (6–12)
        rooms = []
        for loc in locations:
            count = random.randint(6, 12)
            loc_rooms = RoomFactory.create_batch(count, location=loc)
            rooms.extend(loc_rooms)
        self.stdout.write(self.style.SUCCESS(f'Created {len(rooms)} rooms.'))

        # Assign ~90% of users to rooms
        assigned_users = random.sample(users, int(len(users) * 0.9))
        for user in users:
            UserLocationFactory(user=user, room=random.choice(rooms))
            self.stdout.write(self.style.SUCCESS(f'Assigned {len(users)} users to rooms.'))

        # Equipment (2–5 per room)
        equipment = []
        for room in rooms:
            eqs = EquipmentFactory.create_batch(random.randint(2, 5), room=room)
            equipment.extend(eqs)
        self.stdout.write(self.style.SUCCESS(f'Created {len(equipment)} equipment items.'))

        # Components (1–4 per equipment)
        components = []
        for eq in equipment:
            components.extend(ComponentFactory.create_batch(random.randint(1, 4), equipment=eq))
        self.stdout.write(self.style.SUCCESS(f'Created {len(components)} components.'))

        # Accessories (1–3 per room)
        accessories = []
        for room in rooms:
            accessories.extend(AccessoryFactory.create_batch(random.randint(1, 3), room=room))
        self.stdout.write(self.style.SUCCESS(f'Created {len(accessories)} accessories.'))

        # Consumables (2–6 per room)
        consumables = []
        for room in rooms:
            consumables.extend(ConsumableFactory.create_batch(random.randint(2, 6), room=room))
        self.stdout.write(self.style.SUCCESS(f'Created {len(consumables)} consumables.'))

        self.stdout.write(self.style.SUCCESS('Sample data generation completed.'))