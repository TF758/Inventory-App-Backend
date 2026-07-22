from celery import current_app
from django.core.management.base import BaseCommand, CommandError
from django_celery_beat.models import PeriodicTask


class Command(BaseCommand):
    help = "Verify that enabled Celery Beat entries reference registered tasks"

    def handle(self, *args, **options):
        current_app.loader.import_default_modules()
        registered = set(current_app.tasks.keys())

        configured = list(
            PeriodicTask.objects.filter(enabled=True)
            .exclude(task__isnull=True)
            .exclude(task="")
            .values_list("name", "task")
        )
        missing = [
            (name, task_name)
            for name, task_name in configured
            if task_name not in registered
        ]

        if missing:
            details = "\n".join(
                f"- {name}: {task_name}"
                for name, task_name in missing
            )
            raise CommandError(
                "Enabled Celery Beat entries reference unregistered tasks:\n"
                f"{details}"
            )

        self.stdout.write(
            self.style.SUCCESS(
                "Celery task registry verified: "
                f"{len(configured)} enabled Beat entries checked."
            )
        )
