import random
import datetime
import sys

from tqdm import tqdm

from django.core.management.base import BaseCommand
from django.utils import timezone

from db_inventory.models.asset_assignment import AccessoryAssignment, ConsumableIssue, EquipmentAssignment, ReturnRequest, ReturnRequestItem
from db_inventory.models.site import Room
from db_inventory.models.users import User




class Command(BaseCommand):
    help = "Generate realistic asset return data across departments"

    def handle(self, *args, **options):

        self.stdout.write(
            self.style.WARNING("🧹 Purging return history...")
        )

        deleted_items, _ = ReturnRequestItem.objects.all().delete()
        deleted_requests, _ = ReturnRequest.objects.all().delete()

        self.stdout.write(
            self.style.SUCCESS(
                f"✔ Deleted {deleted_requests} requests and {deleted_items} items"
            )
        )
        DAYS = 730
        today = timezone.now()

        self.stdout.write(self.style.WARNING("Generating return data..."))

        users = list(User.objects.all())
        equipment_assignments = list(
            EquipmentAssignment.objects.filter(returned_at__isnull=True)
        )
        accessory_assignments = list(
            AccessoryAssignment.objects.filter(returned_at__isnull=True)
        )
        consumable_issues = list(
            ConsumableIssue.objects.filter(returned_at__isnull=True)
        )
        rooms = list(Room.objects.all())

        if not users:
            self.stdout.write(self.style.ERROR("No users found"))
            return

        total_requests = 0

        # ✅ Enable tqdm only in interactive terminals
        use_tqdm = sys.stdout.isatty()

        pbar = tqdm(
            range(DAYS, 0, -1),
            desc="Generating return days",
            disable=not use_tqdm,
        )

        for day_offset in pbar:
            date = today - datetime.timedelta(days=day_offset)

            # simulate daily load
            num_requests = random.randint(5, 25)

            for _ in range(num_requests):
                requester = random.choice(users)

                # -----------------------------
                # Request status
                # -----------------------------
                status = random.choices(
                    [
                        ReturnRequest.Status.PENDING,
                        ReturnRequest.Status.APPROVED,
                        ReturnRequest.Status.DENIED,
                        ReturnRequest.Status.PARTIAL,
                        ReturnRequest.Status.COMPLETED,
                    ],
                    weights=[0.2, 0.3, 0.1, 0.2, 0.2],
                )[0]

                requested_at = date + datetime.timedelta(
                    hours=random.randint(0, 23),
                    minutes=random.randint(0, 59),
                )

                processed_at = None
                processed_by = None

                if status != ReturnRequest.Status.PENDING:
                    delay_hours = random.randint(1, 72)
                    processed_at = requested_at + datetime.timedelta(hours=delay_hours)
                    processed_by = random.choice(users)

                request = ReturnRequest(
                    requester=requester,
                    status=status,
                    requested_at=requested_at,
                    processed_at=processed_at,
                    processed_by=processed_by,
                    notes="Auto-generated",
                )
                request.save()

                # -----------------------------
                # Items
                # -----------------------------
                num_items = random.randint(1, 4)

                for _ in range(num_items):
                    item_type = random.choice(
                        [
                            ReturnRequestItem.ItemType.EQUIPMENT,
                            ReturnRequestItem.ItemType.ACCESSORY,
                            ReturnRequestItem.ItemType.CONSUMABLE,
                        ]
                    )

                    item_status = random.choices(
                        [
                            ReturnRequestItem.Status.PENDING,
                            ReturnRequestItem.Status.APPROVED,
                            ReturnRequestItem.Status.DENIED,
                        ],
                        weights=[0.3, 0.5, 0.2],
                    )[0]

                    room = random.choice(rooms)

                    kwargs = {
                        "return_request": request,
                        "item_type": item_type,
                        "room": room,
                        "status": item_status,
                        "verified_by": requester if item_status != "pending" else None,
                        "verified_at": processed_at if item_status != "pending" else None,
                        "notes": "Auto-generated",
                    }

                    if (
                        item_type == ReturnRequestItem.ItemType.EQUIPMENT
                        and equipment_assignments
                    ):
                        kwargs["equipment_assignment"] = random.choice(
                            equipment_assignments
                        )

                    elif (
                        item_type == ReturnRequestItem.ItemType.ACCESSORY
                        and accessory_assignments
                    ):
                        acc = random.choice(accessory_assignments)
                        kwargs["accessory_assignment"] = acc
                        kwargs["quantity"] = random.randint(1, acc.quantity)

                    elif (
                        item_type == ReturnRequestItem.ItemType.CONSUMABLE
                        and consumable_issues
                    ):
                        con = random.choice(consumable_issues)
                        kwargs["consumable_issue"] = con
                        kwargs["quantity"] = random.randint(1, con.quantity)

                    item = ReturnRequestItem(**kwargs)
                    item.save()

                total_requests += 1

            pbar.set_postfix(
                {
                    "today": num_requests,
                    "total_requests": total_requests,
                }
            )

        self.stdout.write(
            self.style.SUCCESS(f"Generated {total_requests} return requests")
        )