from django.core.management.base import BaseCommand
from django.conf import settings
from pathlib import Path


APPS = [
    "core",
    "assets",
    "assignments",
    "sites",
    "users",
    "reporting",
    "analytics",
    "data_import",
]


class Command(BaseCommand):
    help = "Deletes migration files for selected apps (keeps __init__.py)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be deleted without deleting files",
        )

    def handle(self, *args, **options):

        dry_run = options["dry_run"]

        if not settings.DEBUG:
            self.stdout.write(
                self.style.ERROR(
                    "Refusing to purge migrations because DEBUG=False (production safety)"
                )
            )
            return

        base_dir = Path(settings.BASE_DIR)

        self.stdout.write(self.style.WARNING("\n🔧 Purging migrations...\n"))

        total_deleted = 0

        for app in APPS:

            migrations_path = base_dir / app / "migrations"

            if not migrations_path.exists():
                self.stdout.write(
                    self.style.WARNING(f"⚠ {app}: migrations folder not found (skipping)")
                )
                continue

            deleted = 0

            for file in migrations_path.iterdir():

                if file.name == "__init__.py":
                    continue

                if file.suffix == ".py":

                    if dry_run:
                        self.stdout.write(f"   DRY RUN → would delete {file}")
                        deleted += 1
                        continue

                    try:
                        file.unlink()
                        deleted += 1
                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(
                                f"❌ {app}: failed to delete {file.name} → {e}"
                            )
                        )

            if deleted == 0:
                self.stdout.write(
                    self.style.WARNING(
                        f"ℹ {app}: no migrations to delete (already clean)"
                    )
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(f"✅ {app}: removed {deleted} migration(s)")
                )

            total_deleted += deleted

        self.stdout.write("\n")

        if dry_run:
            self.stdout.write(
                self.style.WARNING(f"DRY RUN COMPLETE → {total_deleted} files would be deleted")
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f"🎉 Migration purge complete ({total_deleted} files removed)")
            )