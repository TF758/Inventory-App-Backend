
from db_inventory.models.security import Notification


def batched_notification_delete(qs, batch_size=1000):
    """
    Stable cursor-based batch delete.
    Prevents row skipping and avoids large locks.
    """
    total_deleted = 0
    last_id = 0

    while True:
        batch_ids = list(
            qs.filter(id__gt=last_id)
              .order_by("id")
              .values_list("id", flat=True)[:batch_size]
        )

        if not batch_ids:
            break

        deleted, _ = (
            Notification.objects
            .filter(id__in=batch_ids)
            .delete()
        )

        total_deleted += deleted
        last_id = batch_ids[-1]

    return total_deleted


from django.db import connection

def acquire_lock(lock_id: int) -> bool:
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT pg_try_advisory_lock(%s);",
            [lock_id],
        )
        return cursor.fetchone()[0]
    
def batched_delete(qs, batch_size=2000):
    total_deleted = 0

    while True:
        ids = list(qs.values_list("id", flat=True)[:batch_size])
        if not ids:
            break

        deleted, _ = (
            qs.model.objects
            .filter(id__in=ids)
            .delete()
        )
        total_deleted += deleted

    return total_deleted