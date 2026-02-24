from django.db import models
from db_inventory.utils.ids import reserve_public_id
from ulid import ULID

def generate_public_id(prefix: str) -> str:
    return f"{prefix}{str(ULID())}"


class PublicIDRegistry(models.Model):
    """
    Permanent ledger of every public_id ever issued.
    Prevents reuse even if original object is deleted.
    """

    public_id = models.CharField(max_length=32, unique=True, db_index=True)
    model_label = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["model_label"]),
        ]

    def __str__(self):
        return f"{self.public_id} ({self.model_label})"

class PublicIDModel(models.Model):
    """
    Abstract base model that provides a unique public_id field.
    Supports permanent and operational identity strategies.
    """

    public_id = models.CharField(
        max_length=32,
        unique=True,
        editable=False,
        null=True,
        db_index=True,
    )

    PUBLIC_ID_PREFIX = ""
    PUBLIC_ID_PERMANENT = True 

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if not self.public_id:

            if self.PUBLIC_ID_PERMANENT:
                self.public_id = reserve_public_id(
                    prefix=self.PUBLIC_ID_PREFIX,
                    model_label=self._meta.label,
                )
            else:
                self.public_id = generate_public_id(
                    prefix=self.PUBLIC_ID_PREFIX,
                )

        super().save(*args, **kwargs)