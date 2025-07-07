import os
import django

# Set the default Django settings module
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "inventory.settings")

# Setup Django
django.setup()

from django.core.management import call_command

from django.core.management.base import BaseCommand
from db_inventory.factory import (
    UserFactory, AdminUserFactory,
    DepartmentFactory,
    UserDepartmentFactory,
    LocationFactory,
    EquipmentFactory,
    ComponentFactory,
    AccessoryFactory,
    ConsumableFactory
)


class Command(BaseCommand):
    help = 'Generate sample data for the inventory database'

    def handle(self, *args, **kwargs):

        # Clear existing data

        self.stdout.write(self.style.WARNING('Clearing existing data...'))
        call_command('flush', '--no-input')

        self.stdout.write(self.style.SUCCESS('Existing data cleared.'))

        self.stdout.write(self.style.SUCCESS('Generating sample data...'))
        
        # Generate Users
        users = UserFactory.create_batch(10)
        self.stdout.write(self.style.SUCCESS(f'Created {len(users)} users.'))

        admin_user = AdminUserFactory.create_batch(1)
        self.stdout.write(self.style.SUCCESS(f'Created {len(admin_user)} admin user.'))

        # Generate Departments
        departments = DepartmentFactory.create_batch(7)
        self.stdout.write(self.style.SUCCESS(f'Created {len(departments)} departments.'))

        # Generate UserDepartments
        user_departments = UserDepartmentFactory.create_batch(50)
        self.stdout.write(self.style.SUCCESS(f'Created {len(user_departments)} user-department relationships.'))

        # Generate Locations
        locations = LocationFactory.create_batch(5)
        self.stdout.write(self.style.SUCCESS(f'Created {len(locations)} locations.'))

        # Generate Equipment
        equipment = EquipmentFactory.create_batch(20)
        self.stdout.write(self.style.SUCCESS(f'Created {len(equipment)} equipment items.'))

        # Generate Components
        components = ComponentFactory.create_batch(50)
        self.stdout.write(self.style.SUCCESS(f'Created {len(components)} components.'))

        # Generate Accessories
        accessories = AccessoryFactory.create_batch(40)
        self.stdout.write(self.style.SUCCESS(f'Created {len(accessories)} accessories.'))

        # Generate Consumables
        consumables = ConsumableFactory.create_batch(60)
        self.stdout.write(self.style.SUCCESS(f'Created {len(consumables)} consumables.'))

        self.stdout.write(self.style.SUCCESS('Sample data generation completed.'))