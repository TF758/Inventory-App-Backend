
from db_inventory.models.security import Notification


def batched_notification_delete(qs, batch_size=1000):
    """
    Deletes notifications in small batches to avoid long locks.
    Returns total number of deleted rows.
    """
    total_deleted = 0

    while True:
        ids = list(
            qs.values_list("id", flat=True)[:batch_size]
        )
        if not ids:
            break

        deleted, _ = (
            Notification.objects
            .filter(id__in=ids)
            .delete()
        )
        total_deleted += deleted

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