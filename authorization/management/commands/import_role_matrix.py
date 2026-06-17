from pathlib import Path
from time import perf_counter

import pandas as pd
from tqdm import tqdm

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from authorization.models import (
    Permission,
    Role,
    RolePermission,
)


SYSTEM_ROLES = {
    "ROOM_VIEWER": {
        "scope_type": "ROOM",
        "level": 10,
    },
    "ROOM_CLERK": {
        "scope_type": "ROOM",
        "level": 20,
    },
    "ROOM_ADMIN": {
        "scope_type": "ROOM",
        "level": 30,
    },
    "LOCATION_VIEWER": {
        "scope_type": "LOCATION",
        "level": 40,
    },
    "LOCATION_ADMIN": {
        "scope_type": "LOCATION",
        "level": 50,
    },
    "DEPARTMENT_VIEWER": {
        "scope_type": "DEPARTMENT",
        "level": 60,
    },
    "DEPARTMENT_ADMIN": {
        "scope_type": "DEPARTMENT",
        "level": 70,
    },
    "SITE_ADMIN": {
        "scope_type": "GLOBAL",
        "level": 100,
    },
}


class Command(BaseCommand):
    help = "Import role-permission matrix from Excel or CSV"

    def add_arguments(self, parser):
        parser.add_argument(
            "file",
            type=str,
            help="Path to role permission matrix (.xlsx or .csv)"
        )

    @transaction.atomic
    def handle(self, *args, **options):

        start = perf_counter()

        file_path = Path(options["file"])

        if not file_path.exists():
            raise CommandError(
                f"File does not exist: {file_path}"
            )

        df = self._load_file(file_path)

        if "Permission" not in df.columns:
            raise CommandError(
                "Spreadsheet must contain a 'Permission' column."
            )

        self.stdout.write("")
        self.stdout.write("=" * 60)
        self.stdout.write("IMPORTING ROLE MATRIX")
        self.stdout.write("=" * 60)

        self._sync_roles()

        roles = {
            role.code: role
            for role in Role.objects.all()
        }

        permissions_created = 0
        permissions_processed = 0

        mappings_created = 0
        mappings_removed = 0

        role_columns = [
            column
            for column in df.columns
            if column != "Permission"
        ]

        self._validate_role_columns(role_columns)

        for _, row in tqdm(
            df.iterrows(),
            total=len(df),
            desc="Importing permissions",
            unit="permission",
        ):

            permission_code = str(
                row["Permission"]
            ).strip()

            if not permission_code:
                continue

            permissions_processed += 1

            module = permission_code.split(".")[0]

            permission, created = (
                Permission.objects.get_or_create(
                    code=permission_code,
                    defaults={
                        "name": permission_code,
                        "module": module,
                        "description": "",
                        "is_system": True,
                    }
                )
            )

            if created:
                permissions_created += 1

            for role_code in role_columns:

                role = roles[role_code]

                enabled = self._cell_to_bool(
                    row[role_code]
                )

                existing = (
                    RolePermission.objects.filter(
                        role=role,
                        permission=permission
                    )
                )

                if enabled:

                    _, created = (
                        RolePermission.objects.get_or_create(
                            role=role,
                            permission=permission
                        )
                    )

                    if created:
                        mappings_created += 1

                else:

                    deleted_count, _ = (
                        existing.delete()
                    )

                    mappings_removed += deleted_count

        elapsed = perf_counter() - start

        self.stdout.write("")
        self.stdout.write("=" * 60)
        self.stdout.write("IMPORT SUMMARY")
        self.stdout.write("=" * 60)

        self.stdout.write(
            self.style.SUCCESS(
                f"Permissions processed: {permissions_processed}"
            )
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Permissions created: {permissions_created}"
            )
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Mappings created: {mappings_created}"
            )
        )

        self.stdout.write(
            self.style.WARNING(
                f"Mappings removed: {mappings_removed}"
            )
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Completed in {elapsed:.2f}s"
            )
        )

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "Role matrix import complete."
            )
        )

    def _load_file(self, file_path):

        suffix = file_path.suffix.lower()

        if suffix == ".xlsx":
            return pd.read_excel(file_path)

        if suffix == ".csv":
            return pd.read_csv(file_path)

        raise CommandError(
            "Only .xlsx and .csv files are supported."
        )

    def _cell_to_bool(self, value):

        if pd.isna(value):
            return False

        value = str(value).strip()

        return value == "1"

    def _validate_role_columns(self, role_columns):

        expected = set(
            SYSTEM_ROLES.keys()
        )

        actual = set(role_columns)

        missing = expected - actual

        if missing:
            raise CommandError(
                f"Missing role columns: {sorted(missing)}"
            )

    def _sync_roles(self):

        self.stdout.write("")

        for role_code, config in tqdm(
            SYSTEM_ROLES.items(),
            desc="Syncing roles",
            unit="role",
        ):

            Role.objects.update_or_create(
                code=role_code,
                defaults={
                    "name": role_code.replace(
                        "_",
                        " "
                    ).title(),
                    "scope_type": config["scope_type"],
                    "level": config["level"],
                    "is_system_role": True,
                }
            )