from django.core.management.base import BaseCommand

from authorization.models import Role
from users.models.roles import RoleAssignment


class Command(BaseCommand):
    help = "Backfill RoleAssignment.role_ref from legacy role field"

    def handle(self, *args, **options):

        roles = {
            role.code: role
            for role in Role.objects.all()
        }

        updated = 0
        missing = set()

        queryset = RoleAssignment.objects.filter(
            role_ref__isnull=True
        )

        total = queryset.count()

        self.stdout.write(
            f"Found {total} assignments to backfill."
        )

        for assignment in queryset:

            role = roles.get(
                assignment.role
            )

            if not role:
                missing.add(
                    assignment.role
                )
                continue

            assignment.role_ref = role

            assignment.save(
                update_fields=[
                    "role_ref"
                ]
            )

            updated += 1

            if updated % 500 == 0:
                self.stdout.write(
                    f"Updated {updated}"
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"Updated {updated} assignments."
            )
        )

        if missing:
            self.stdout.write(
                self.style.WARNING(
                    "Missing roles: "
                    + ", ".join(
                        sorted(missing)
                    )
                )
            )

        remaining = (
            RoleAssignment.objects.filter(
                role_ref__isnull=True
            ).count()
        )

        self.stdout.write(
            f"Remaining without role_ref: {remaining}"
        )