

from django.conf import settings
from db_inventory.models.base import PublicIDModel
from db_inventory.models.site import Department, Location,Room
from django.db import models
from db_inventory.models.users import User
from django.utils import timezone
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType


class AuditLog(PublicIDModel):
    """ 
    audit log for security, and traceability.
    """

    PUBLIC_ID_PREFIX = "LOG"

    user = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name="audit_logs",)

    # Snapshots (in case user is deleted or renamed)
    user_public_id = models.CharField(max_length=15, null=True, blank=True)
    user_email = models.EmailField(null=True, blank=True)


    event_type = models.CharField(max_length=100,help_text="Machine-readable event identifier",)
    description = models.TextField(blank=True,default="",help_text="Human-readable description of the event")
    metadata = models.JSONField(null=True,blank=True,help_text="Additional structured event data",)


    target_model = models.CharField(max_length=100,null=True,blank=True,help_text="Model name of the affected object",)

    target_id = models.CharField(max_length=100,null=True,blank=True,help_text="Public ID of the affected object")
    target_name = models.CharField(max_length=255,null=True,blank=True,help_text="Snapshot of object name at time of event",)

    department = models.ForeignKey(Department,on_delete=models.SET_NULL,null=True,blank=True,related_name="audit_logs",)
    department_name = models.CharField(max_length=100, null=True, blank=True)

    location = models.ForeignKey(Location,on_delete=models.SET_NULL,null=True,blank=True,related_name="audit_logs",)
    location_name = models.CharField(max_length=255, null=True, blank=True)

    room = models.ForeignKey(Room,on_delete=models.SET_NULL,null=True,blank=True,related_name="audit_logs",)
    room_name = models.CharField(max_length=255, null=True, blank=True)



    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, null=True, blank=True)

    created_at = models.DateTimeField(default=timezone.now,db_index=True,)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["event_type"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["user"]),
            models.Index(fields=["target_model", "target_id"]),
        ]

    def save(self, *args, **kwargs):
        if self.pk:
            raise RuntimeError("AuditLog records are immutable and cannot be modified.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise RuntimeError("AuditLog records cannot be deleted.")

    def __str__(self):
        actor = self.user_email or self.user_public_id or "System"
        return f"{self.event_type} by {actor} @ {self.created_at:%Y-%m-%d %H:%M:%S}"

    # --------------------
    # Common event constants
    # --------------------

    class Events:
        LOGIN = "login"
        LOGOUT = "logout"
        USER_CREATED = "user_created"
        USER_UPDATED = "user_updated"
        ADMIN_UPDATED_USER = "admin_updated_user"
        USER_DELETED = "user_deleted"

        PASSWORD_RESET_REQUESTED = "password_reset_requested"
        PASSWORD_RESET_COMPLETED = "password_reset_completed"

        ROLE_ASSIGNED = "role_assigned"
        ROLE_REVOKED = "role_revoked"

        MODEL_CREATED = "model_created"
        MODEL_UPDATED = "model_updated"
        MODEL_DELETED = "model_deleted"

        MODEL_RELOCATED = "model_relocated"

        USER_MOVED = "user_moved"
        EXPORT_GENERATED = "export_generated"
        ASSET_ASSIGNED = "asset_assigned"
        ASSET_UNASSIGNED = "asset_unassigned"
        ASSET_REASSIGNED = "asset_reassigned"
        EQUIPMENT_STATUS_CHANGED = "equipment_status_changed"


class SiteNameChangeHistory(models.Model):
    """
    Records explicit rename events for site entities
    (Department, Location, Room), keyed by public_id.
    """

    class SiteType(models.TextChoices):
        DEPARTMENT = "department", "Department"
        LOCATION = "location", "Location"
        ROOM = "room", "Room"

    site_type = models.CharField(max_length=20,choices=SiteType.choices,db_index=True,)


    object_public_id = models.CharField( max_length=15,db_index=True,help_text="Public ID of the renamed site entity",)

    old_name = models.CharField(max_length=255)
    new_name = models.CharField(max_length=255)

    changed_at = models.DateTimeField(auto_now_add=True)

    user = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name="site_name_change_histories",)
    user_email = models.EmailField(null=True, blank=True)

    reason = models.TextField(blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["site_type", "object_public_id"]),
            models.Index(fields=["changed_at"]),
        ]
        ordering = ["-changed_at"]

    def __str__(self):
        return f"{self.site_type}: {self.old_name} → {self.new_name}"
    

class SiteRelocationHistory(models.Model):
    """
    Records structural relocation of site entities:
    - Location moved between Departments
    - Room moved between Locations

    All *_name fields are snapshots taken at the time of relocation.
    """

    class SiteType(models.TextChoices):
        LOCATION = "location", "Location"
        ROOM = "room", "Room"

    site_type = models.CharField(max_length=20,choices=SiteType.choices,db_index=True,)


    object_public_id = models.CharField(max_length=15,db_index=True,help_text="Public ID of the relocated site entity",)
    object_name = models.CharField(max_length=255,help_text="Name of the site at time of relocation", null=True)


    from_parent_public_id = models.CharField(max_length=15,help_text="Previous parent site public ID",)
    from_parent_name = models.CharField(max_length=255,help_text="Previous parent site name at time of relocation", null=True)

    to_parent_public_id = models.CharField(max_length=15,help_text="New parent site public ID",)
    to_parent_name = models.CharField(max_length=255,help_text="New parent site name at time of relocation", null=True)

    changed_at = models.DateTimeField(auto_now_add=True)

    user = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name="site_relocations",)
    user_email = models.EmailField(null=True, blank=True)

    reason = models.TextField(blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["site_type", "object_public_id"]),
            models.Index(fields=["changed_at"]),
        ]
        ordering = ["-changed_at"]

    def __str__(self):
        return (
            f"{self.site_type}: {self.object_name} "
            f"({self.from_parent_name} → {self.to_parent_name})"
        )