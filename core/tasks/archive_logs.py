import gzip
import shutil
import time
from pathlib import Path
from datetime import datetime, timedelta

from celery import shared_task
from django.conf import settings

from core.models.tasks import ScheduledTaskRun

import logging

logger = logging.getLogger("arms.logs")


@shared_task(bind=True)
def archive_logs(self):
    start_ts = time.monotonic()

    run = ScheduledTaskRun.objects.create(
        task_name="archive_logs",
        status=ScheduledTaskRun.Status.STARTED,
        message="Starting log archive process",
    )

    logs_dir = Path(settings.LOGS_DIR)
    archive_dir = logs_dir / "archive"
    archive_dir.mkdir(exist_ok=True)

    cutoff = datetime.now() - timedelta(days=settings.LOG_ARCHIVE_AFTER_DAYS)

    archived = 0
    skipped = 0

    try:
        for file in logs_dir.iterdir():
            name = file.name

            # Skip active logs
            if name in ("app.log", "error.log"):
                continue

            # Only process rotated logs
            if not name.endswith(".log"):
                continue

            try:
                date_str = name.split(".")[0]  # YYYY-MM-DD
                file_date = datetime.strptime(date_str, "%Y-%m-%d")
            except Exception:
                skipped += 1
                continue

            if file_date > cutoff:
                skipped += 1
                continue

            gz_path = archive_dir / f"{name}.gz"

            with open(file, "rb") as f_in:
                with gzip.open(gz_path, "wb") as f_out:
                    shutil.copyfileobj(f_in, f_out)

            file.unlink()
            archived += 1

        run.status = ScheduledTaskRun.Status.SUCCESS
        run.message = f"archived={archived}, skipped={skipped}"

        logger.info(
            "log_archive_completed",
            extra={
                "archived": archived,
                "skipped": skipped,
            },
        )

        return {
            "archived": archived,
            "skipped": skipped,
        }

    except Exception as exc:
        run.status = ScheduledTaskRun.Status.FAILED
        run.message = str(exc)

        logger.exception(
            "log_archive_failed",
            extra={"error": str(exc)},
        )

        raise

    finally:
        run.duration_ms = int((time.monotonic() - start_ts) * 1000)
        run.save()