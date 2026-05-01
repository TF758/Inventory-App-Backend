from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = "Create load testing users"

    def add_arguments(self, parser):
        parser.add_argument("--count", type=int, default=30)
        parser.add_argument("--password", type=str, default="LoadTest123!")

    def handle(self, *args, **options):
        count = options["count"]
        password = options["password"]

        created = 0

        for i in range(1, count + 1):
            email = f"loadtest{i:02d}@example.com"

            if User.objects.filter(email=email).exists():
                continue

            User.objects.create_user(
                email=email,
                password=password,
                fname="Load",
                lname=f"User{i:02d}",
                is_active=True,
            )

            created += 1

        self.stdout.write(
            self.style.SUCCESS(f"Created {created} load test users")
        )