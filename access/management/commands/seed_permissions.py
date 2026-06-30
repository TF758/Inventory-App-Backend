from pathlib import Path

import pandas as pd

from django.conf import settings
from django.core.management.base import BaseCommand

from access.models import Permission


REQUIRED_COLUMNS = [
    "Domain",
    "Permission",
    "Label",
    "Description",
    "Scope Type",
    "Sort Order",
    "Configurable",
]


TRUE_VALUES = {
    "1",
    "TRUE",
    "Y",
    "YES",
}

FALSE_VALUES = {
    "0",
    "FALSE",
    "N",
    "NO",
}


def clean_text(value, default=""):
    if pd.isna(value):
        return default

    return str(value).strip()


def parse_bool(value, default=False):
    if pd.isna(value):
        return default

    normalized = str(value).strip().upper()

    if normalized in TRUE_VALUES:
        return True

    if normalized in FALSE_VALUES:
        return False

    return default


def parse_int(value, default=0):
    if pd.isna(value):
        return default

    try:
        return int(value)

    except (TypeError, ValueError):
        return default


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

        missing_columns = [
            column
            for column in REQUIRED_COLUMNS
            if column not in df.columns
        ]

        if missing_columns:
            self.stdout.write(
                self.style.ERROR(
                    "Sheet2 is missing required columns: "
                    + ", ".join(missing_columns)
                )
            )
            return

        created = 0
        updated = 0
        skipped = 0

        for _, row in df.iterrows():
            code = clean_text(row["Permission"])

            if not code:
                skipped += 1
                continue

            _, was_created = Permission.objects.update_or_create(
                code=code,
                defaults={
                    "name": clean_text(
                        row["Label"],
                        default=code,
                    ),
                    "domain": clean_text(
                        row["Domain"],
                    ),
                    "scope_type": clean_text(
                        row["Scope Type"],
                    ),
                    "description": clean_text(
                        row["Description"],
                    ),
                    "sort_order": parse_int(
                        row["Sort Order"],
                    ),
                    "is_configurable": parse_bool(
                        row["Configurable"],
                        default=True,
                    ),
                },
            )

            if was_created:
                created += 1
            else:
                updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                "Permissions seeded. "
                f"Created={created}, Updated={updated}, Skipped={skipped}"
            )
        )