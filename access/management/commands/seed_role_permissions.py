from pathlib import Path

import pandas as pd

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from access.models import (
    Permission,
    RolePermission,
)
from users.models.roles import RoleAssignment


ROLE_COLUMNS = [
    role
    for role, _ in RoleAssignment.ROLE_CHOICES
    if role != "SITE_ADMIN"
]


TRUE_VALUES = {
    "1",
    "TRUE",
    "Y",
    "YES",
}


class Command(BaseCommand):
    help = "Seed role permission mappings from permissions.xlsx"

    def handle(self, *args, **kwargs):
        file_path = (
            Path(settings.BASE_DIR)
            / "permissions.xlsx"
        )

        if not file_path.exists():
            self.stdout.write(
                self.style.ERROR(
                    f"File not found: {file_path}"
                )
            )
            return

        df = pd.read_excel(
            file_path,
            sheet_name="Sheet1",
        )

        required_columns = [
            "Permission",
            *ROLE_COLUMNS,
        ]

        missing_columns = [
            column
            for column in required_columns
            if column not in df.columns
        ]

        if missing_columns:
            self.stdout.write(
                self.style.ERROR(
                    "Sheet1 is missing required columns: "
                    + ", ".join(missing_columns)
                )
            )
            return

        created = 0
        skipped_unknown = 0
        skipped_non_configurable = 0

        with transaction.atomic():
            deleted_count, _ = (
                RolePermission.objects
                .all()
                .delete()
            )

            self.stdout.write(
                f"Removed {deleted_count} existing role permissions"
            )

            for _, row in df.iterrows():
                permission_code = str(
                    row["Permission"]
                ).strip()

                if not permission_code:
                    continue

                try:
                    permission = Permission.objects.get(
                        code=permission_code,
                    )

                except Permission.DoesNotExist:
                    skipped_unknown += 1

                    self.stdout.write(
                        self.style.WARNING(
                            f"Permission not found: {permission_code}"
                        )
                    )

                    continue

                if not permission.is_configurable:
                    skipped_non_configurable += 1

                    self.stdout.write(
                        self.style.WARNING(
                            "Skipping non-configurable permission "
                            f"from Sheet1: {permission_code}"
                        )
                    )

                    continue

                for role in ROLE_COLUMNS:
                    value = row[role]

                    if pd.isna(value):
                        allowed = False
                    else:
                        allowed = (
                            str(value).strip().upper()
                            in TRUE_VALUES
                        )

                    if not allowed:
                        continue

                    RolePermission.objects.create(
                        role=role,
                        permission=permission,
                    )

                    created += 1

        self.stdout.write(
            self.style.SUCCESS(
                "Role permissions seeded. "
                f"Created={created}, "
                f"Unknown={skipped_unknown}, "
                f"NonConfigurable={skipped_non_configurable}"
            )
        )