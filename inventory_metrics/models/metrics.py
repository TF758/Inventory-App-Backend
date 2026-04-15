
# from django.db import models


# class DailySystemMetrics(models.Model):
#     date = models.DateField(unique=True)

#     # User metrics
#     total_users = models.PositiveIntegerField(default=0)
#     human_users = models.PositiveIntegerField(default=0)
#     system_users = models.PositiveIntegerField(default=0)
#     active_users_last_24h = models.PositiveIntegerField(default=0)
#     active_users_last_7d = models.PositiveIntegerField(default=0)
#     new_users_last_24h = models.PositiveIntegerField(default=0)
#     locked_users = models.PositiveIntegerField(default=0)

#     # Session metrics
#     total_sessions = models.PositiveIntegerField(default=0)
#     active_sessions = models.PositiveIntegerField(default=0)
#     revoked_sessions = models.PositiveIntegerField(default=0)
#     expired_sessions_last_24h = models.PositiveIntegerField(default=0)
#     unique_users_logged_in_last_24h = models.PositiveIntegerField(default=0)

#     # Inventory metrics
#     total_equipment = models.PositiveIntegerField(default=0)
#     equipment_ok = models.PositiveIntegerField(default=0)
#     equipment_under_repair = models.PositiveIntegerField(default=0)
#     equipment_damaged = models.PositiveIntegerField(default=0)

#     total_components = models.PositiveIntegerField(default=0)
#     total_components_quantity = models.PositiveIntegerField(default=0)
#     total_consumables = models.PositiveIntegerField(default=0)
#     total_consumables_quantity = models.PositiveIntegerField(default=0)
#     total_accessories = models.PositiveIntegerField(default=0)
#     total_accessories_quantity = models.PositiveIntegerField(default=0)

#     schema_version = models.PositiveSmallIntegerField(default=1)
#     created_at = models.DateTimeField(auto_now_add=True)

#     class Meta:
#         ordering = ["-date"]
#         verbose_name = "Daily System Metric"
#         verbose_name_plural = "Daily System Metrics"

#     def __str__(self):
#         return f"DailySystemMetrics - {self.date.isoformat()}"
    
# class DailyAuthMetrics(models.Model):
#     date = models.DateField(unique=True, db_index=True)

#     # Login events
#     total_logins = models.PositiveIntegerField(default=0)
#     unique_users_logged_in = models.PositiveIntegerField(default=0)
#     failed_logins = models.PositiveIntegerField(default=0)
#     lockouts = models.PositiveIntegerField(default=0)

#     # Sessions
#     active_sessions = models.PositiveIntegerField(default=0)
#     revoked_sessions = models.PositiveIntegerField(default=0)
#     expired_sessions = models.PositiveIntegerField(default=0)
#     users_multiple_active_sessions = models.PositiveIntegerField(default=0)
#     users_with_revoked_sessions = models.PositiveIntegerField(default=0)

#     # Password resets
#     password_resets_started = models.PositiveIntegerField(default=0)
#     password_resets_completed = models.PositiveIntegerField(default=0)
#     active_password_resets = models.PositiveIntegerField(default=0)
#     expired_password_resets = models.PositiveIntegerField(default=0)

#     schema_version = models.PositiveSmallIntegerField(default=1)
#     created_at = models.DateTimeField(auto_now_add=True)

#     class Meta:
#         ordering = ["-date"]
#         verbose_name = "Daily Auth Metric"
#         verbose_name_plural = "Daily Auth Metrics"

#     def __str__(self):
#         return f"DailyAuthMetrics - {self.date}"


# class DailyReturnMetrics(models.Model):
#     date = models.DateField(unique=True, db_index=True)

#     total_requests = models.PositiveIntegerField(default=0)
#     pending_requests = models.PositiveIntegerField(default=0)
#     approved_requests = models.PositiveIntegerField(default=0)
#     denied_requests = models.PositiveIntegerField(default=0)
#     partial_requests = models.PositiveIntegerField(default=0)
#     completed_requests = models.PositiveIntegerField(default=0)

#     requests_created_last_24h = models.PositiveIntegerField(default=0)
#     requests_processed_last_24h = models.PositiveIntegerField(default=0)

#     total_items = models.PositiveIntegerField(default=0)
#     pending_items = models.PositiveIntegerField(default=0)
#     approved_items = models.PositiveIntegerField(default=0)
#     denied_items = models.PositiveIntegerField(default=0)

#     equipment_items = models.PositiveIntegerField(default=0)
#     accessory_items = models.PositiveIntegerField(default=0)
#     consumable_items = models.PositiveIntegerField(default=0)

#     avg_processing_time_seconds= models.PositiveIntegerField(default=0)
#     max_processing_time_seconds = models.PositiveIntegerField(default=0)

#     schema_version = models.PositiveSmallIntegerField(default=1)
#     created_at = models.DateTimeField(auto_now_add=True)

#     class Meta:
#         ordering = ["-date"]