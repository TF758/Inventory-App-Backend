from pathlib import Path

import pandas as pd

from django.conf import settings
from django.core.management.base import BaseCommand

from access.models import Permission


class Command(BaseCommand):
    help = "Seed Permission records from permissions.xlsx"

    def handle(self, *args, **kwargs):

        file_path = Path(settings.BASE_DIR) / "permissions.xlsx"

        if not file_path.exists():
            self.stdout.write(
                self.style.ERROR(
                    f"File not found: {file_path}"
                )
            )
            return

        df = pd.read_excel(
            file_path,
            sheet_name="Sheet2",
        )

        created = 0
        updated = 0

        for _, row in df.iterrows():

            _, was_created = Permission.objects.update_or_create(
                code=row["Permission"],
                defaults={
                    "name": row["Description"],
                    "domain": row["Domain"],
                    "scope_type": (
                        row["Scope Type"]
                        if pd.notna(row["Scope Type"])
                        else ""
                    ),
                    "description": (
                        row["Notes"]
                        if pd.notna(row["Notes"])
                        else ""
                    ),
                },
            )

            if was_created:
                created += 1
            else:
                updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Permissions seeded. Created={created}, Updated={updated}"
            )
        )