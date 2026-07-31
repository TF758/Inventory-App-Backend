import uuid

from django.core.files.base import ContentFile
from django.core.files.storage import storages
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = (
        "Verify read, write, and delete access for application "
        "storage aliases."
    )

    aliases = ("default", "reports")

    def handle(self, *args, **options):
        del args, options

        for alias in self.aliases:
            storage = storages[alias]
            requested_name = (
                f"_health/deployment-{uuid.uuid4().hex}.txt"
            )
            stored_name = ""

            try:
                stored_name = storage.save(
                    requested_name,
                    ContentFile(b"inventory-storage-check"),
                )

                with storage.open(stored_name, "rb") as stored_file:
                    if stored_file.read() != b"inventory-storage-check":
                        raise CommandError(
                            f"Storage alias '{alias}' returned "
                            "unexpected content."
                        )
            except Exception as exc:
                raise CommandError(
                    f"Storage alias '{alias}' failed its "
                    f"read/write check: {exc}"
                ) from exc
            finally:
                if stored_name:
                    try:
                        storage.delete(stored_name)
                    except Exception as cleanup_exc:
                        raise CommandError(
                            f"Storage alias '{alias}' could not "
                            f"delete its check object: {cleanup_exc}"
                        ) from cleanup_exc

            self.stdout.write(
                self.style.SUCCESS(
                    f"Storage alias '{alias}' verified."
                )
            )
