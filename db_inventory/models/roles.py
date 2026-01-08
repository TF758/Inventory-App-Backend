from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone

from db_inventory.models.base import PublicIDModel
from db_inventory.models.site import Department, Location, Room
from django.conf import settings
from django.db.models import Q

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
    department = models.ForeignKey(Department,on_delete=models.CASCADE,null=True,blank=True,related_name="role_assignments",)
    location = models.ForeignKey(Location,on_delete=models.CASCADE,null=True,blank=True,related_name="role_assignments",)
    room = models.ForeignKey(Room,on_delete=models.CASCADE,null=True,blank=True,related_name="role_assignments",)

    assigned_by = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name="assigned_roles",)
    assigned_date = models.DateTimeField(default=timezone.now)

    class Meta:
        indexes = [
            models.Index(fields=["public_id"]),
            models.Index(fields=["role"]),
            models.Index(fields=["user", "role"]),
        ]

        constraints = [
            # --------------------------------------------------
            # Scope validity (exactly one scope, except SITE_ADMIN)
            # --------------------------------------------------
            models.CheckConstraint(
                condition=(
                    # SITE_ADMIN → no scope
                    Q(role="SITE_ADMIN") &
                    Q(department__isnull=True) &
                    Q(location__isnull=True) &
                    Q(room__isnull=True)
                ) |
                (
                    # Department roles → department only
                    Q(role__startswith="DEPARTMENT") &
                    Q(department__isnull=False) &
                    Q(location__isnull=True) &
                    Q(room__isnull=True)
                ) |
                (
                    # Location roles → location only
                    Q(role__startswith="LOCATION") &
                    Q(department__isnull=True) &
                    Q(location__isnull=False) &
                    Q(room__isnull=True)
                ) |
                (
                    # Room roles → room only
                    Q(role__startswith="ROOM") &
                    Q(department__isnull=True) &
                    Q(location__isnull=True) &
                    Q(room__isnull=False)
                ),
                name="role_assignment_valid_scope",
            ),

            # --------------------------------------------------
            # Uniqueness constraints (NULL-safe, scope-aware)
            # --------------------------------------------------

            # Only one SITE_ADMIN per user
            models.UniqueConstraint(
                fields=["user", "role"],
                condition=Q(role="SITE_ADMIN"),
                name="unique_site_admin_per_user",
            ),

            # One department role per user per department
            models.UniqueConstraint(
                fields=["user", "role", "department"],
                condition=Q(department__isnull=False),
                name="unique_department_role_per_user",
            ),

            # One location role per user per location
            models.UniqueConstraint(
                fields=["user", "role", "location"],
                condition=Q(location__isnull=False),
                name="unique_location_role_per_user",
            ),

            # One room role per user per room
            models.UniqueConstraint(
                fields=["user", "role", "room"],
                condition=Q(room__isnull=False),
                name="unique_room_role_per_user",
            ),
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
            if self.department or self.location or self.room:
                raise ValidationError("SITE_ADMIN role must not have any scope.")
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
