from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.db import transaction


class Command(BaseCommand):
    help = "Master database seeding command (runs all seeders in order)"

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("🌱 Starting database seeding"))

        steps = [
            ("Government / site data", "generate_govt_data"),
            ( "Agreement data", "generate_agreement_data", ),
            ("Equipment history", "generate_equipment_history"),
            ("Accessory history", "generate_accessory_history"),
            ("Consumable data", "generate_consumable_history"),
            ("Audit history", "generate_audit_history"),
        ]

        for label, command in steps:
            self.stdout.write(self.style.MIGRATE_HEADING(f"➡ {label}"))

            try:
                with transaction.atomic():
                    call_command(command)
            except Exception as exc:
                self.stderr.write(
                    self.style.ERROR(
                        f"❌ Failed while running '{command}': {exc}"
                    )
                )
                raise  # fail fast

            self.stdout.write(self.style.SUCCESS(f"✔ {label} complete"))

        self.stdout.write(self.style.SUCCESS("🎉 Database seeding completed successfully"))
