from django.db import models

from users.models.roles import RoleAssignment


class Permission(models.Model):
    domain = models.CharField(
        max_length=100,
        db_index=True,
    )

    code = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
    )

    name = models.CharField(
        max_length=255,
    )

    scope_type = models.CharField(
        max_length=50,
        blank=True,
    )

    description = models.TextField(
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = [
            "domain",
            "code",
        ]

    def __str__(self):
        return self.code


class RolePermission(models.Model):
    role = models.CharField(
        max_length=40,
        choices=RoleAssignment.ROLE_CHOICES,
        db_index=True,
    )

    permission = models.ForeignKey(
        Permission,
        on_delete=models.CASCADE,
        related_name="role_permissions",
    )

    class Meta:
        ordering = [
            "role",
            "permission__domain",
            "permission__code",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=["role", "permission"],
                name="unique_role_permission",
            )
        ]

    def __str__(self):
        return (
            f"{self.get_role_display()} → "
            f"{self.permission.code}"
        )