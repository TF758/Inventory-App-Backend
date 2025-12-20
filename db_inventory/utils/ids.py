import secrets
import uuid

BASE62_ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"


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


def generate_prefixed_id(prefix: str, length: int = 10) -> str:
    """
    Generate a prefixed Base62 ID (no uniqueness check).
    Uniqueness MUST be enforced by caller.
    """
    u = uuid.uuid4().int >> 64
    return f"{prefix}{int_to_base62(u)[:length]}"
