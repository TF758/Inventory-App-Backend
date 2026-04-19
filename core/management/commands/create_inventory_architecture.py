from django.core.management.base import BaseCommand
from pathlib import Path


APPS = [
    "core",
    "assets",
    "assignments",
    "sites",
    "users",
    "reporting",
    "analytics",
    "data_import",
]


APP_STRUCTURE = {
    "models": [],
    "services": [],
    "selectors": [],
    "tasks": [],
    "utils": [],
    "urls": [],
    "tests": [],
    "api": [
        "serializers",
        "viewsets"
    ],
}


class Command(BaseCommand):
    help = "Create the full inventory domain architecture"

    def handle(self, *args, **kwargs):

        for app_name in APPS:

            base_dir = Path(app_name)

            if base_dir.exists():
                self.stdout.write(f"Skipping {app_name} (already exists)")
                continue

            base_dir.mkdir()

            # base files
            (base_dir / "__init__.py").touch()

            (base_dir / "apps.py").write_text(
f"""from django.apps import AppConfig


class {app_name.capitalize()}Config(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "{app_name}"
"""
            )

            # create folders
            for folder, subfolders in APP_STRUCTURE.items():

                folder_path = base_dir / folder
                folder_path.mkdir()

                (folder_path / "__init__.py").touch()

                for sub in subfolders:
                    sub_path = folder_path / sub
                    sub_path.mkdir()
                    (sub_path / "__init__.py").touch()

            self.stdout.write(self.style.SUCCESS(f"Created {app_name}"))

        self.stdout.write(
            self.style.SUCCESS("\nAdd these to INSTALLED_APPS:\n")
        )

        for app in APPS:
            self.stdout.write(f'    "{app}",')

