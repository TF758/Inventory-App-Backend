from django.db import models
from db_inventory.utils.ids import reserve_public_id


class PublicIDRegistry(models.Model):
    """
    Permanent ledger of every public_id ever issued.

    This prevents reuse even if the original object is deleted.
    """

    public_id = models.CharField( max_length=32, unique=True, db_index=True, )
    model_label = models.CharField( max_length=100, help_text="app_label.ModelName that reserved this id", )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["model_label"]),
        ]

    def __str__(self):
        return f"{self.public_id} ({self.model_label})"

class PublicIDModel(models.Model):
    """Abstract base model that provides a unique public_id field."""

    public_id = models.CharField(
        max_length=32,
        unique=True,
        editable=False,
        null=True,
        db_index=True,
    )

    PUBLIC_ID_PREFIX = ""

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if not self.public_id:
          

            self.public_id = reserve_public_id(
                prefix=self.PUBLIC_ID_PREFIX,
                model_label=self._meta.label,
            )

        super().save(*args, **kwargs)