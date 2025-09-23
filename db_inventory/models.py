import secrets
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, UserManager
from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
import uuid
import hashlib
from django.db import models
from django.conf import settings

BASE62_ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"

def int_to_base62(num):
    """Convert an integer to a Base62 string."""
    if num == 0:
        return BASE62_ALPHABET[0]
    chars = []
    base = len(BASE62_ALPHABET)
    while num > 0:
        num, rem = divmod(num, base)
        chars.append(BASE62_ALPHABET[rem])
    return "".join(reversed(chars))

def generate_base62_identifier(length=12):
    """Generate a random Base62 identifier."""
    random_int = secrets.randbits(length * 6)  # ~6 bits per char in base62
    return int_to_base62(random_int).rjust(length, BASE62_ALPHABET[0])

def generate_prefixed_public_id(model_class, prefix, length=10):
    """Generate a unique public_id with a prefix."""
    while True:
        candidate = prefix + generate_base62_identifier(length)
        if not model_class.objects.filter(public_id=candidate).exists():
            return candidate

class CustomUserManager(UserManager):
    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("You have not provided a valid e-mail address")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email=None, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email=None, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self._create_user(email, password, **extra_fields)

class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(blank=True, default='', unique=True, db_index=True)
    fname = models.CharField(max_length=30, blank=True, default='')
    lname = models.CharField(max_length=30, blank=True, default='')
    job_title = models.CharField(max_length=50, blank=True, default='')
    role = models.CharField(max_length=20, blank=True, default='user')
    public_id = models.CharField(max_length=15, unique=True, editable=False, null=True, db_index=True)
    active_role = models.ForeignKey(
        "RoleAssignment",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="active_for_users", 
    )

    is_active = models.BooleanField(default=True)
    is_superuser = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)

    date_joined = models.DateTimeField(default=timezone.now)
    last_login = models.DateTimeField(blank=True, null=True)

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    EMAIL_FIELD = 'email'
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    # def __str__(self):
    #     return self.get_full_name()

    def __str__(self):
        return self.email 

    def get_full_name(self):
        return self.fname + ' ' + self.lname if self.fname or self.lname else self.email

    def get_short_name(self):
        return self.fname if self.fname else self.email.split('@')[0]

    def save(self, *args, **kwargs):
        if not self.public_id:
            while True:
                candidate = generate_base62_identifier(length=12)
                if not User.objects.filter(public_id=candidate).exists():
                    self.public_id = candidate
                    break
        super().save(*args, **kwargs)

class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, default='')
    img_link = models.URLField(blank=True, default='')
    public_id = models.CharField(max_length=12, unique=True, editable=False, null=True, db_index=True)


    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.public_id:
            self.public_id = generate_prefixed_public_id(Department, prefix="DPT")
        super().save(*args, **kwargs)

class Location(models.Model):
    name = models.CharField(max_length=255)
    department = models.ForeignKey(Department, on_delete=models.PROTECT, null=True)
    public_id = models.CharField(max_length=12, unique=True, editable=False, null=True, db_index=True)

    def __str__(self):
        return self.name + ' @ ' + self.department.name
    
    def save(self, *args, **kwargs):
        if not self.public_id:
            self.public_id = generate_prefixed_public_id(Location, prefix="LOC")
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = 'Location'
        verbose_name_plural = 'Locations'

class Room(models.Model):
    location = models.ForeignKey(Location, on_delete=models.PROTECT, related_name='rooms')
    name = models.CharField(max_length=255)
    public_id = models.CharField(max_length=12, unique=True, editable=False, null=True, db_index=True)

    def save(self, *args, **kwargs):
        if not self.public_id:
            self.public_id = generate_prefixed_public_id(Room, prefix="RM")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} @ {self.location.name}"

class UserLocation(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    room = models.ForeignKey(Room, on_delete=models.CASCADE, null=True, blank=True)
    date_joined = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ('user', 'room')
        verbose_name = 'User Room'
        verbose_name_plural = 'User Rooms'

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.room.name if self.room else 'No Room'}"

class Equipment(models.Model):
    name = models.CharField(max_length=100)
    brand = models.CharField(max_length=100, blank=True, default="")
    model = models.CharField(max_length=100, blank=True, default="")
    serial_number = models.CharField(max_length=100, unique=True, blank=True, null=True)
    public_id = models.CharField(max_length=12, unique=True, editable=False, null=True, db_index=True)
    room = models.ForeignKey(Room, on_delete=models.CASCADE, null=True, blank=True)

    # def __str__(self):
    #     return self.name

    def save(self, *args, **kwargs):
        if not self.public_id:
            self.public_id = generate_prefixed_public_id(Equipment, prefix="EQ")
        super().save(*args, **kwargs)

class Component(models.Model):
    name = models.CharField(max_length=100)
    brand = models.CharField(max_length=100, blank=True, default='')
    model = models.CharField(max_length=100, blank=True, default='')
    serial_number = models.CharField(max_length=100, unique=True, blank=True, null=True)
    quantity = models.IntegerField(default=0)
    public_id = models.CharField(max_length=12, unique=True, editable=False, null=True, db_index=True)
    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return self.name + ' @ ' + self.equipment.name

    def save(self, *args, **kwargs):
        if not self.public_id:
            self.public_id = generate_prefixed_public_id(Component, prefix="COM")
        super().save(*args, **kwargs)

class Consumable(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, default='')
    quantity = models.IntegerField(default=0)
    room = models.ForeignKey(Room, on_delete=models.CASCADE, null=True, blank=True)
    public_id = models.CharField(max_length=12, unique=True, editable=False, null=True, db_index=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.public_id:
            self.public_id = generate_prefixed_public_id(Consumable, prefix="CON")
        super().save(*args, **kwargs)

class Accessory(models.Model):
    name = models.CharField(max_length=100)
    serial_number = models.CharField(max_length=100, unique=True, blank=True, null=True)
    quantity = models.IntegerField(default=0)
    public_id = models.CharField(max_length=12, unique=True, editable=False, null=True, db_index=True)
    room = models.ForeignKey(Room, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.public_id:
            self.public_id = generate_prefixed_public_id(Accessory, prefix="AC")
        super().save(*args, **kwargs)

class RoleAssignment(models.Model):
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

    user = models.ForeignKey("User", on_delete=models.CASCADE,  related_name="role_assignments",)
    role = models.CharField(max_length=40, choices=ROLE_CHOICES)

    department = models.ForeignKey("Department", on_delete=models.CASCADE, null=True, blank=True,related_name="role_assignments" )
    location = models.ForeignKey("Location", on_delete=models.CASCADE, null=True, blank=True, related_name="role_assignments")
    room = models.ForeignKey("Room", on_delete=models.CASCADE, null=True, blank=True, related_name="role_assignments")

    public_id = models.CharField(max_length=12, unique=True, editable=False, null=True, db_index=True)

    assigned_by = models.ForeignKey("User", on_delete=models.CASCADE,  null=True, blank=True )
    assigned_date =  models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ("user", "role", "department", "location", "room")

    def clean(self):
        """
        Enforce that the correct scope field is filled for each role.
        """
        if self.role == "SITE_ADMIN":
            # Site Admin: no restrictions, can span everything
            return

        # Department-level roles
        if self.role in ["DEPARTMENT_ADMIN", "DEPARTMENT_VIEWER"]:
            if not self.department:
                raise ValidationError("Department must be provided for Department roles.")
            if self.location or self.room:
                raise ValidationError("Department roles cannot have Location or Room assigned.")

        # Location-level roles
        elif self.role in ["LOCATION_ADMIN", "LOCATION_VIEWER"]:
            if not self.location:
                raise ValidationError("Location must be provided for Location roles.")
            if self.department or self.room:
                raise ValidationError("Location roles cannot have Department or Room assigned.")

        # Room-level roles
        elif self.role in ["ROOM_ADMIN", "ROOM_VIEWER", "ROOM_CLERK"]:
            if not self.room:
                raise ValidationError("Room must be provided for Room roles.")
            if self.department or self.location:
                raise ValidationError("Room roles cannot have Department or Location assigned.")

        else:
            raise ValidationError(f"Unknown role: {self.role}")
        

    def get_role_id(self):
        return self.public_id
        


    def save(self, *args, **kwargs):
        # Run model validation before saving
        self.full_clean()

        # Auto-generate a public ID if missing
        if not self.public_id:
            self.public_id = generate_prefixed_public_id(
                RoleAssignment, prefix="RA"
            )

        return super().save(*args, **kwargs)

        
    def __str__(self):
        """
        Human-readable representation of the role assignment.
        Example: "Alice Smith - Room Admin (Room: Conference Room A)"
        """
        if self.role == "SITE_ADMIN":
            scope = "Entire Site"
        elif self.role.startswith("DEPARTMENT") and self.department:
            scope = f"Department: {self.department}"
        elif self.role.startswith("LOCATION") and self.location:
            scope = f"Location: {self.location}"
        elif self.role.startswith("ROOM") and self.room:
            scope = f"Room: {self.room}"
        else:
            scope = "Unscoped"

        return f"{self.user.get_full_name()} - {self.get_role_display()} ({scope})"
    
   

class UserSession(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        REVOKED = "revoked", "Revoked"
        EXPIRED = "expired", "Expired"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sessions"
    )
    refresh_token_hash = models.CharField(max_length=128, unique=True)
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.ACTIVE
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    last_used_at = models.DateTimeField(auto_now=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=256, null=True, blank=True)

    def mark_revoked(self):
        self.status = self.Status.REVOKED
        self.save(update_fields=["status"])

    def is_active(self):
        return self.status == self.Status.ACTIVE and self.expires_at >= timezone.now()

    @staticmethod
    def hash_token(raw_token: str) -> str:
        """Hash refresh token before storing or comparing."""
        return hashlib.sha256(raw_token.encode()).hexdigest()

    def __str__(self):
        return f"Session {self.id} for {self.user} ({self.status})"