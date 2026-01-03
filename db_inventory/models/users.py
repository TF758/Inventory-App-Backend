from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, UserManager
from django.utils import timezone
from db_inventory.utils.ids import generate_base62_identifier



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
    active_role = models.ForeignKey("RoleAssignment",on_delete=models.SET_NULL,null=True,blank=True,related_name="active_for_users", )
    
    created_by = models.ForeignKey("User",on_delete=models.SET_NULL,null=True,blank=True,related_name="created_users")
    is_locked = models.BooleanField(default=False)
    is_system_user = models.BooleanField(default=False)  # for test/demo/system accounts
    force_password_change = models.BooleanField(default=False)
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

        indexes = [
        models.Index(fields=["public_id"]),
        models.Index(fields=["email"]),
        models.Index(fields=["role"]),
        models.Index(fields=["is_active"]),
    ]


    def __str__(self):
        return self.email 

    def get_full_name(self):
        parts = [self.fname, self.lname]
        return " ".join(p for p in parts if p).strip() or self.email

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

class PasswordResetEvent(models.Model):
    user = models.ForeignKey(User,on_delete=models.CASCADE,related_name="password_reset_events")
    admin = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="admin_password_resets")
    token = models.CharField(max_length=255, db_index=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)  
    created_at = models.DateTimeField(auto_now_add=True)

    def is_valid(self):
        return (
            self.used_at is None
            and self.expires_at >= timezone.now()
        )

    def mark_used(self):
        self.used_at = timezone.now()
        self.save(update_fields=["used_at"])
