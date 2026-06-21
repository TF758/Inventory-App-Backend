from pathlib import Path

import pandas as pd

from django.conf import settings
from django.core.management.base import BaseCommand

from access.models import Permission, RolePermission


ROLE_COLUMNS = [
    "ROOM_VIEWER",
    "ROOM_CLERK",
    "ROOM_ADMIN",
    "LOCATION_VIEWER",
    "LOCATION_ADMIN",
    "DEPARTMENT_VIEWER",
    "DEPARTMENT_ADMIN",
    "SITE_ADMIN",
]


class Command(BaseCommand):
    help = "Seed role permission mappings from permissions.xlsx"

    def handle(self, *args, **kwargs):

        file_path = Path(settings.BASE_DIR) / "permissions.xlsx"

        if not file_path.exists():
            self.stdout.write(
                self.style.ERROR(
                    f"File not found: {file_path}"
                )
            )
            return

        # Update this sheet name if your matrix lives elsewhere
        df = pd.read_excel(
            file_path,
            sheet_name="Sheet1",
        )

        created = 0

        for _, row in df.iterrows():

            permission_code = row["Permission"]

            try:
                permission = Permission.objects.get(
                    code=permission_code
                )
            except Permission.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(
                        f"Permission not found: {permission_code}"
                    )
                )
                continue

            for role in ROLE_COLUMNS:

                value = row.get(role)

                if pd.isna(value):
                    continue

                allowed = str(value).strip() in [
                    "1",
                    "TRUE",
                    "True",
                    "true",
                    "Y",
                    "YES",
                    "Yes",
                ]

                if not allowed:
                    continue

                _, was_created = (
                    RolePermission.objects.get_or_create(
                        role=role,
                        permission=permission,
                    )
                )

                if was_created:
                    created += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Created {created} role permissions"
            )
        )