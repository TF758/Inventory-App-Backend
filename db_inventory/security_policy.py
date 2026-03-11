"""
Security policy resolver.

Provides cached access to runtime-configurable security settings
with safe fallbacks to Django settings.

Used by authentication, session management, and login flows.
"""

from datetime import timedelta
from django.conf import settings
from django.core.cache import cache

from db_inventory.models.security import SecuritySettings


# ---------------------------------------------------------
# Cache configuration
# ---------------------------------------------------------

CACHE_KEY = "security_policy_settings"
CACHE_TTL = 300  # seconds (5 minutes)


# ---------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------

def _get_security_settings():
    """
    Fetch SecuritySettings from cache or database.
    """
    sec = cache.get(CACHE_KEY)

    if sec is not None:
        return sec

    sec = SecuritySettings.objects.first()
    cache.set(CACHE_KEY, sec, CACHE_TTL)

    return sec


def invalidate_security_policy_cache():
    """
    Clear cached security policy.
    Call this when SecuritySettings is updated.
    """
    cache.delete(CACHE_KEY)


# ---------------------------------------------------------
# Session policies
# ---------------------------------------------------------

def get_session_idle_timeout():
    """
    Idle session timeout.
    """
    sec = _get_security_settings()

    if sec and sec.session_idle_minutes:
        return timedelta(minutes=sec.session_idle_minutes)

    return settings.SESSION_IDLE_TIMEOUT


def get_session_absolute_lifetime():
    """
    Absolute maximum session lifetime.
    """
    sec = _get_security_settings()

    if sec and sec.session_absolute_hours:
        return timedelta(hours=sec.session_absolute_hours)

    return settings.SESSION_ABSOLUTE_LIFETIME


# ---------------------------------------------------------
# Token policies
# ---------------------------------------------------------

def get_access_token_lifetime():
    
    return settings.SIMPLE_JWT.get("ACCESS_TOKEN_LIFETIME")


# ---------------------------------------------------------
# Session policy
# ---------------------------------------------------------

def get_max_concurrent_sessions():
    """
    Maximum allowed active sessions per user.
    """
    sec = _get_security_settings()

    if sec and sec.max_concurrent_sessions:
        return sec.max_concurrent_sessions

    return getattr(settings, "MAX_CONCURRENT_SESSIONS", 5)


# ---------------------------------------------------------
# Account security policies
# ---------------------------------------------------------

def get_lockout_attempts():
    """
    Failed login attempts before account lock.
    """
    sec = _get_security_settings()

    if sec and sec.lockout_attempts:
        return sec.lockout_attempts

    return getattr(settings, "LOCKOUT_ATTEMPTS", 5)


def get_lockout_duration():
    """
    Account lock duration.
    """
    sec = _get_security_settings()

    if sec and sec.lockout_duration_minutes:
        return timedelta(minutes=sec.lockout_duration_minutes)

    return getattr(settings, "LOCKOUT_DURATION", timedelta(minutes=15))