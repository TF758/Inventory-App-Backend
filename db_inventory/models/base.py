from django.db import models
from db_inventory.utils.ids import generate_prefixed_id, reserve_public_id
from ulid import ULID

def generate_public_id(prefix: str) -> str:
    return f"{prefix}{str(ULID())}"

class PublicIDQuerySet(models.QuerySet):

    def bulk_create(self, objs, **kwargs):

        objs_without_id = [o for o in objs if not o.public_id]

        if objs_without_id:

            model = objs_without_id[0].__class__

            ids = [
                generate_prefixed_id(model.PUBLIC_ID_PREFIX)
                for _ in range(len(objs_without_id))
            ]

            # assign ids
            for obj, pid in zip(objs_without_id, ids):
                obj.public_id = pid

            # create registry rows
            registry_rows = [
                PublicIDRegistry(
                    public_id=pid,
                    model_label=model._meta.label
                )
                for pid in ids
            ]

            PublicIDRegistry.objects.bulk_create(registry_rows)

        return super().bulk_create(objs, **kwargs)

class PublicIDManager(models.Manager.from_queryset(PublicIDQuerySet)):
    pass


class PublicIDModel(models.Model):
    """
    Abstract base model that provides a unique public_id field.
    Supports permanent and operational identity strategies.
    """

    public_id = models.CharField(
        max_length=32,
        unique=True,
        editable=False,
        blank=True,
        null=False,
        db_index=True,
    )

    PUBLIC_ID_PREFIX = ""
    PUBLIC_ID_PERMANENT = True

    objects = PublicIDManager()

    class Meta:
        abstract = True

    def ensure_public_id(self):

        if self.public_id:
            return

        if not self.PUBLIC_ID_PREFIX:
            raise ValueError(
                f"{self.__class__.__name__} must define PUBLIC_ID_PREFIX"
            )

        if self.PUBLIC_ID_PERMANENT:
            self.public_id = reserve_public_id(
                prefix=self.PUBLIC_ID_PREFIX,
                model_label=self._meta.label,
            )
        else:
            self.public_id = generate_prefixed_id(
                prefix=self.PUBLIC_ID_PREFIX,
            )

    def save(self, *args, **kwargs):
        self.ensure_public_id()
        super().save(*args, **kwargs)


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