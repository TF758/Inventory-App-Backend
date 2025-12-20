


from db_inventory.models.base import PublicIDModel
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone

class Department(PublicIDModel):
    PUBLIC_ID_PREFIX = "DPT"

    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, default='')
    img_link = models.URLField(blank=True, default='')

    class Meta:
        indexes = [
            models.Index(fields=["public_id"]),
            models.Index(fields=["name"]),
        ]

    def __str__(self):
        return self.name



class Location(PublicIDModel):
    PUBLIC_ID_PREFIX = "LOC"

    name = models.CharField(max_length=255)
    department = models.ForeignKey(Department,on_delete=models.SET_NULL,null=True,related_name="locations")

    class Meta:
        verbose_name = "Location"
        verbose_name_plural = "Locations"
        indexes = [
            models.Index(fields=["public_id"]),
            models.Index(fields=["name"]),
        ]

    def __str__(self):
        if self.department:
            return f"{self.name} @ {self.department.name}"
        return self.name

class Room(PublicIDModel):
    PUBLIC_ID_PREFIX = "RM"

    location = models.ForeignKey(Location,on_delete=models.SET_NULL, null=True,related_name="rooms")
    name = models.CharField(max_length=255)

    class Meta:
        indexes = [
            models.Index(fields=["public_id"]),
            models.Index(fields=["name"]),
        ]

    def __str__(self):
        if self.location:
            return f"{self.name} @ {self.location.name}"
        return self.name
    


class UserLocation(PublicIDModel):
    """
    Tracks the physical room assignment history of a user.
    Only one location may be marked as current per user.
    """

    PUBLIC_ID_PREFIX = "UL"

    user = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE, related_name="user_locations",)
    room = models.ForeignKey(Room, on_delete=models.SET_NULL,null=True,blank=True,related_name="user_locations",)

    is_current = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "User Room"
        verbose_name_plural = "User Rooms"
        indexes = [
            models.Index(fields=["public_id"]),
            models.Index(fields=["user"]),
            models.Index(fields=["is_current"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["user"],
                condition=models.Q(is_current=True),
                name="unique_current_location_per_user",
            )
        ]

    # --------------------
    # Validation
    # --------------------

    def clean(self):
        """
        Prevent assigning the same user to the same room more than once.
        """
        if self.room and UserLocation.objects.filter(
            user=self.user,
            room=self.room
        ).exclude(pk=self.pk).exists():
            raise ValidationError(
                "This user is already assigned to this room."
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        room = self.room.name if self.room else "No Room"
        return f"{self.user} – {room}"