from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, UserManager
from django.db import models
from django.utils import timezone
from django.utils.text import slugify
import hashlib
import uuid
from django.core.exceptions import ValidationError


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
    email = models.EmailField(blank=True, default='', unique=True)
    fname = models.CharField(max_length=30, blank=True, default='')
    lname = models.CharField(max_length=30, blank=True, default='')
    job_title = models.CharField(max_length=50, blank=True, default='')
    role = models.CharField(max_length=20, blank=True, default='user')

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
    
    def get_full_name(self):
        return self.fname + ' ' + self.lname if self.fname or self.lname else self.email
    
    def get_short_name(self):
        return self.fname + ' ' + self.lname if self.fname or self.lname else self.email or self.email.split('@')[0]
    
   

class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, default='')

    def __str__(self):
        return self.name
    

    class Meta:
        verbose_name = 'Department'
        verbose_name_plural = 'Departments'

class Location(models.Model):
    name = models.CharField(max_length=255, blank=True, default='')
    room = models.CharField(max_length=255, blank=True, default='')
    area = models.CharField(max_length=100, blank=True, default='')
    section = models.CharField(max_length=100, blank=True, default='')
    department = models.ForeignKey(Department, on_delete=models.PROTECT)
   

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Location'
        verbose_name_plural = 'Locations'


class UserLocation(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    location = models.ForeignKey(Location, on_delete=models.CASCADE)
    date_joined = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ('user', 'location')
        verbose_name = 'User Location'
        verbose_name_plural = 'User Locations'
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.location.name}"


class Equipment(models.Model):
    name = models.CharField(max_length=100, unique=True)
    brand = models.CharField(max_length=100, blank=True, default='')
    model = models.CharField(max_length=100, blank=True, default='')
    serial_number = models.CharField(max_length=100, unique=True, blank=True, null=True)
    identifier = models.CharField(max_length=255, unique=True, editable=False, blank=True)
    location = models.ForeignKey(Location, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return self.name
    
    def generate_identifier(self):
        """
        Generate a hashed identifier using:
        - SHA-1 hash of slugified name+brand+model
        - a short UUID segment
        Example: abc123ef45-a1b2c3
        """
        base_slug = slugify(f"{self.name}-{self.brand}-{self.model or ''}")
        hash_digest = hashlib.sha1(base_slug.encode()).hexdigest()[:10]
        uuid_segment = uuid.uuid4().hex[:6]
        return f"EQ{hash_digest}-{uuid_segment}"

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        if is_new:
            # Step 1: Save the instance to assign a primary key
            super().save(*args, **kwargs)
            # Step 2: Now that pk is available, generate identifier and save again
            if not self.identifier:
                self.identifier = self.generate_identifier()
                super().save(update_fields=["identifier"])
        else:
            # For updates, prevent identifier from changing
            old = Equipment.objects.filter(pk=self.pk).first()
            if old and old.identifier != self.identifier:
                raise ValidationError("Identifier is immutable and cannot be changed.")
            super().save(*args, **kwargs)

    class Meta:
        verbose_name = 'Equipment'
        verbose_name_plural = 'Equipments'
        


class Component(models.Model):
    name = models.CharField(max_length=100, unique=True)
    brand = models.CharField(max_length=100, blank=True, default='')
    model = models.CharField(max_length=100, blank=True, default='')
    serial_number = models.CharField(max_length=100, unique=True, blank=True, null=True)
    quantity = models.IntegerField(default=0)
    identifier = models.CharField(max_length=255, unique=True, editable=False, blank=True)
    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return self.name
    
    def generate_identifier(self):
        """
        Generate a hashed identifier using:
        - SHA-1 hash of slugified name+brand+model
        - a short UUID segment
        Example: abc123ef45-a1b2c3
        """
        base_slug = slugify(f"{self.name}-{self.brand}-{self.model or ''}")
        hash_digest = hashlib.sha1(base_slug.encode()).hexdigest()[:10]
        uuid_segment = uuid.uuid4().hex[:6]
        return f"C{hash_digest}-{uuid_segment}"

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        if is_new:
            # Step 1: Save the instance to assign a primary key
            super().save(*args, **kwargs)
            # Step 2: Now that pk is available, generate identifier and save again
            if not self.identifier:
                self.identifier = self.generate_identifier()
                super().save(update_fields=["identifier"])
        else:
            # For updates, prevent identifier from changing
            old = Equipment.objects.filter(pk=self.pk).first()
            if old and old.identifier != self.identifier:
                raise ValidationError("Identifier is immutable and cannot be changed.")
            super().save(*args, **kwargs)

    class Meta:
        verbose_name = 'Component'
        verbose_name_plural = 'Components'


class Accessory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    serial_number = models.CharField(max_length=100, unique=True, blank=True, null=True)
    quantity = models.IntegerField(default=0)
    location = models.ForeignKey(Location, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Accessory'
        verbose_name_plural = 'Accessories'


class Consumable(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, default='')
    quantity = models.IntegerField(default=0)
    location = models.ForeignKey(Location, on_delete=models.CASCADE, null=True, blank=True)
    



