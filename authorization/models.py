from django.db import models

from core.models.base import PublicIDModel


class ScopeType(models.TextChoices):
    ROOM = "ROOM", "Room"
    LOCATION = "LOCATION", "Location"
    DEPARTMENT = "DEPARTMENT", "Department"
    GLOBAL = "GLOBAL", "Global"


class Permission(PublicIDModel):
    """
    Atomic capability.

    Examples:
        assets.view
        assets.create
        users.transfer
        reports.generate
    """

    PUBLIC_ID_PREFIX = "PER"

    code = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
    )

    name = models.CharField(
        max_length=100,
    )

    description = models.TextField(
        blank=True,
    )

    module = models.CharField(
        max_length=50,
        db_index=True,
    )

    is_system = models.BooleanField(
        default=True,
    )

    class Meta:
        ordering = ["module", "code"]

        indexes = [
            models.Index(fields=["module"]),
            models.Index(fields=["is_system"]),
        ]

    def __str__(self):
        return self.code


class Role(PublicIDModel):
    """
    Collection of permissions.

    IMPORTANT:
    level is used ONLY for administrative authority
    (assigning/managing roles).

    Permissions determine application capabilities.
    """

    PUBLIC_ID_PREFIX = "ROL"

    # Stable identifier used internally
    code = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
    )

    # Human-readable label
    name = models.CharField(
        max_length=100,
    )

    description = models.TextField(
        blank=True,
    )

    scope_type = models.CharField(
        max_length=20,
        choices=ScopeType.choices,
    )

    # Administrative authority only
    level = models.PositiveIntegerField(
        default=0,
    )

    is_system_role = models.BooleanField(
        default=False,
    )

    permissions = models.ManyToManyField(
        Permission,
        related_name="roles",
        blank=True,
    )

    class Meta:
        ordering = ["level", "name"]

        indexes = [
            models.Index(fields=["code"]),
            models.Index(fields=["scope_type"]),
            models.Index(fields=["level"]),
            models.Index(fields=["is_system_role"]),
        ]

    def __str__(self):
        return self.name