from .base import env

# -------------------------------------------------
# Notification retention (days)
# -------------------------------------------------

# -------------------------------
# Auto-read grace periods
# -------------------------------

NOTIF_INFO_AUTO_READ_DAYS = env.int( "NOTIF_INFO_AUTO_READ_DAYS", default=7, )

NOTIF_WARNING_AUTO_READ_DAYS = env.int( "NOTIF_WARNING_AUTO_READ_DAYS", default=14, )

NOTIF_CRITICAL_AUTO_READ_DAYS = env.int( "NOTIF_CRITICAL_AUTO_READ_DAYS", default=30, )

# -------------------------------
# Soft delete after read
# -------------------------------

NOTIF_INFO_LIFETIME_DAYS = env.int( "NOTIF_INFO_LIFETIME_DAYS", default=7, )

NOTIF_WARNING_LIFETIME_DAYS = env.int( "NOTIF_WARNING_LIFETIME_DAYS", default=14, )

NOTIF_CRITICAL_LIFETIME_DAYS = env.int( "NOTIF_CRITICAL_LIFETIME_DAYS", default=90, )

# -------------------------------
# Hard delete after soft delete
# -------------------------------

NOTIF_INFO_PURGE_DAYS = env.int( "NOTIF_INFO_PURGE_DAYS", default=3, )

NOTIF_WARNING_PURGE_DAYS = env.int( "NOTIF_WARNING_PURGE_DAYS", default=7, )

NOTIF_CRITICAL_PURGE_DAYS = env.int( "NOTIF_CRITICAL_PURGE_DAYS", default=30, )