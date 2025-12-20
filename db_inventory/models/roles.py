from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone

from db_inventory.models.base import PublicIDModel
from db_inventory.models.site import Department, Location, Room
from django.conf import settings


class RoleAssignment(PublicIDModel):
    """
    Assigns a role to a user at a specific scope
    (site / department / location / room).
    """

    PUBLIC_ID_PREFIX = "RA"

    ROLE_CHOICES = [
        # Room roles
        ("ROOM_VIEWER", "Room Viewer"),
        ("ROOM_CLERK", "Room Clerk"),
        ("ROOM_ADMIN", "Room Admin"),

        # Location roles
        ("LOCATION_VIEWER", "Location Viewer"),
        ("LOCATION_ADMIN", "Location Admin"),

        # Department roles
        ("DEPARTMENT_VIEWER", "Department Viewer"),
        ("DEPARTMENT_ADMIN", "Department Admin"),

        # Global
        ("SITE_ADMIN", "Site Admin"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="role_assignments",
    )

    role = models.CharField(max_length=40, choices=ROLE_CHOICES)

    # Scope (only ONE may be set, depending on role)
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="role_assignments",
    )
    location = models.ForeignKey(
        Location,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="role_assignments",
    )
    room = models.ForeignKey(
        Room,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="role_assignments",
    )

    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_roles",
    )
    assigned_date = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ("user", "role", "department", "location", "room")
        indexes = [
            models.Index(fields=["public_id"]),
            models.Index(fields=["role"]),
        ]

    # --------------------
    # Validation
    # --------------------

    def clean(self):
        """
        Enforce that the correct scope is set for each role.
        """
        # SITE_ADMIN: no scope required
        if self.role == "SITE_ADMIN":
            return

        # Department-level roles
        if self.role.startswith("DEPARTMENT"):
            if not self.department:
                raise ValidationError("Department must be set for Department roles.")
            if self.location or self.room:
                raise ValidationError("Department roles cannot have Location or Room.")

        # Location-level roles
        elif self.role.startswith("LOCATION"):
            if not self.location:
                raise ValidationError("Location must be set for Location roles.")
            if self.department or self.room:
                raise ValidationError("Location roles cannot have Department or Room.")

        # Room-level roles
        elif self.role.startswith("ROOM"):
            if not self.room:
                raise ValidationError("Room must be set for Room roles.")
            if self.department or self.location:
                raise ValidationError("Room roles cannot have Department or Location.")

        else:
            raise ValidationError(f"Unknown role: {self.role}")

    def save(self, *args, **kwargs):
        # Enforce validation at save-time
        self.full_clean()
        super().save(*args, **kwargs)

    # --------------------
    # Helpers
    # --------------------

    def __str__(self):
        if self.role == "SITE_ADMIN":
            scope = "Entire Site"
        elif self.department:
            scope = f"Department: {self.department.name}"
        elif self.location:
            scope = f"Location: {self.location.name}"
        elif self.room:
            scope = f"Room: {self.room.name}"
        else:
            scope = "Unscoped"

        return f"{self.user} – {self.get_role_display()} ({scope})"
