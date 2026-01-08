from django.db import models
from db_inventory.utils.ids import generate_prefixed_id

class PublicIDModel(models.Model):

    """Abstract base model that provides a unique public_id field."""

    public_id = models.CharField(
        max_length=32,
        unique=True,
        editable=False,
        null=True,
        db_index=True
    )

    PUBLIC_ID_PREFIX = ""

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if not self.public_id:
            for _ in range(5):
                candidate = generate_prefixed_id(self.PUBLIC_ID_PREFIX)
                if not self.__class__.objects.filter(public_id=candidate).exists():
                    self.public_id = candidate
                    break
            else:
                raise RuntimeError("Failed to generate unique public_id")

        super().save(*args, **kwargs)
