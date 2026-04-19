import secrets
import uuid
from typing import Iterable
from django.db import models
from django.apps import apps


BASE62_ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"

from django.db import IntegrityError, transaction


def int_to_base62(num: int) -> str:
    """Convert an integer to a Base62 string."""
    if num == 0:
        return BASE62_ALPHABET[0]

    chars = []
    base = len(BASE62_ALPHABET)
    while num > 0:
        num, rem = divmod(num, base)
        chars.append(BASE62_ALPHABET[rem])
    return "".join(reversed(chars))


def generate_base62_identifier(length: int = 12) -> str:
    """Generate a random Base62 identifier."""
    random_int = secrets.randbits(length * 6)  # ~6 bits per char
    return int_to_base62(random_int).rjust(length, BASE62_ALPHABET[0])


def generate_unique_prefixed_id(model_class, prefix, max_attempts=5):
    for _ in range(max_attempts):
        public_id = generate_prefixed_id(prefix)
        if not model_class.objects.filter(public_id=public_id).exists():
            return public_id
    raise RuntimeError("Failed to generate unique public_id")

def generate_prefixed_id(prefix: str, length: int = 10) -> str:
    """
    Generate a prefixed Base62 ID (no uniqueness check).
    Uniqueness MUST be enforced by caller.
    """
    u = uuid.uuid4().int >> 64
    return f"{prefix}{int_to_base62(u)[:length]}"

def generate_public_ids(objs: Iterable[models.Model]):
    """
    Assign public_id to any object that looks like a PublicIDModel.

    Behavior:
    - Permanent IDs → reserved in PublicIDRegistry
    - Ephemeral IDs → generated locally (no registry)

    Still duck-typed to avoid model imports.
    """

    for obj in objs:
        if hasattr(obj, "PUBLIC_ID_PREFIX") and not getattr(obj, "public_id", None):

            permanent = getattr(obj, "PUBLIC_ID_PERMANENT", True)

            if permanent:
                obj.public_id = reserve_public_id(
                    prefix=obj.PUBLIC_ID_PREFIX,
                    model_label=obj._meta.label,
                )
            else:
                obj.public_id = generate_prefixed_id(
                    prefix=obj.PUBLIC_ID_PREFIX,
                )

    return objs


def reserve_public_id(prefix: str, model_label: str) -> str:
    """
    Reserve a globally unique public_id via PublicIDRegistry.

    Concurrency-safe:
    - DB unique constraint enforces uniqueness
    - Retries on collision
    """

    PublicIDRegistry = apps.get_model("core", "PublicIDRegistry")

    for _ in range(20):
        candidate = generate_prefixed_id(prefix)

        try:
            with transaction.atomic():
                PublicIDRegistry.objects.create(
                    public_id=candidate,
                    model_label=model_label,
                )
            return candidate

        except IntegrityError:
            # collision or concurrent reservation
            continue

    raise RuntimeError("Failed to reserve unique public_id")

