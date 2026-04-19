from django.core.management.base import BaseCommand
from django.apps import apps
from django.db import transaction
from tqdm import tqdm # progress bar
from core.models.base import PublicIDModel, PublicIDRegistry




class Command(BaseCommand):
    help = "Backfill PublicIDRegistry from existing PublicIDModel rows"

    def add_arguments(self, parser):
        parser.add_argument(
            "--batch-size",
            type=int,
            default=1000,
            help="Number of rows to process per batch",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Do not write to DB",
        )

    def handle(self, *args, **options):

        batch_size = options["batch_size"]
        dry_run = options["dry_run"]

        total_created = 0
        total_existing = 0

        self.stdout.write(self.style.WARNING("Starting PublicIDRegistry backfill..."))

        for model in apps.get_models():

            # Skip abstract models
            if model._meta.abstract:
                continue

            # Only process subclasses of PublicIDModel
            if not issubclass(model, PublicIDModel):
                continue

            # Avoid processing the registry itself
            if model is PublicIDRegistry:
                continue

            model_label = model._meta.label

            self.stdout.write(f"\nProcessing {model_label}")

            qs = (
                model.objects
                .exclude(public_id__isnull=True)
                .values_list("public_id", flat=True)
            )

            buffer = []

            for public_id in tqdm(qs.iterator(chunk_size=batch_size), desc=model_label):

                buffer.append(public_id)

                if len(buffer) >= batch_size:
                    created, existing = self._flush(buffer, model_label, dry_run)

                    total_created += created
                    total_existing += existing

                    buffer.clear()

            # flush remaining
            if buffer:
                created, existing = self._flush(buffer, model_label, dry_run)

                total_created += created
                total_existing += existing

        self.stdout.write(self.style.SUCCESS("\nBackfill completed"))
        self.stdout.write(f"Created: {total_created}")
        self.stdout.write(f"Already existed: {total_existing}")

    def _flush(self, public_ids, model_label, dry_run):

        if not public_ids:
            return 0, 0

        existing_ids = set(
            PublicIDRegistry.objects
            .filter(public_id__in=public_ids)
            .values_list("public_id", flat=True)
        )

        to_create = [
            PublicIDRegistry(
                public_id=pid,
                model_label=model_label,
            )
            for pid in public_ids
            if pid not in existing_ids
        ]

        if dry_run:
            return len(to_create), len(existing_ids)

        with transaction.atomic():

            PublicIDRegistry.objects.bulk_create(
                to_create,
                ignore_conflicts=True,  # protects against concurrent runs
            )

        return len(to_create), len(existing_ids)