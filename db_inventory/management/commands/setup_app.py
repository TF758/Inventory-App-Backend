from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.db import transaction


class Command(BaseCommand):
    help = "Full application setup (seed data, backfill, history, schedulers)"

    def add_arguments(self, parser):
        parser.add_argument("--skip-seed", action="store_true")
        parser.add_argument("--skip-backfill", action="store_true")
        parser.add_argument("--skip-history", action="store_true")
        parser.add_argument("--skip-periodic", action="store_true")
        parser.add_argument("--skip-cleaners", action="store_true")
        parser.add_argument("--skip-return-requests", action="store_true")
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.MIGRATE_HEADING("🚀 Starting full application setup")
        )

        steps = [
            {
                "label": "🌱 Seed database",
                "command": "seed_db",
                "skip": options["skip_seed"],
                "kwargs": {},
            },
            {
                "label": "🆔 Backfill Public ID Registry",
                "command": "backfill_public_id_registry",
                "skip": options["skip_backfill"],
                "kwargs": {"dry_run": options["dry_run"]},
            },
            {
                "label": "📊 Generate historical analytics",
                "command": "generate_history",
                "skip": options["skip_history"],
                "kwargs": {},
            },
            {
                "label": "📊 Generate Return Request Data",
                "command": "generate_asset_return_data",
                "skip": options["skip_return_requests"],
                "kwargs": {},
            },
            {
                "label": "⏱ Setup periodic data tasks",
                "command": "generate_periodic_data",
                "skip": options["skip_periodic"],
                "kwargs": {},
            },
            {
                "label": "🧹 Setup DB cleaners",
                "command": "setup_db_cleaners",
                "skip": options["skip_cleaners"],
                "kwargs": {},
            },
        ]

        for step in steps:
            if step["skip"]:
                self.stdout.write(
                    self.style.WARNING(f"⏭ Skipping: {step['label']}")
                )
                continue

            self.stdout.write(
                self.style.MIGRATE_HEADING(f"➡ {step['label']}")
            )

            try:
                with transaction.atomic():
                    call_command(step["command"], **step["kwargs"])
            except Exception as exc:
                self.stderr.write(
                    self.style.ERROR(
                        f"❌ Failed during '{step['command']}': {exc}"
                    )
                )
                raise

            self.stdout.write(
                self.style.SUCCESS(f"✔ Completed: {step['label']}")
            )

        self.stdout.write(
            self.style.SUCCESS("🎉 Application setup completed successfully")
        )