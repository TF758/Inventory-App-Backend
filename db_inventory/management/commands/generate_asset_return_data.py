import random
import datetime
import sys

from tqdm import tqdm

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction

from db_inventory.models.asset_assignment import (
    AccessoryAssignment,
    ConsumableIssue,
    EquipmentAssignment,
    ReturnRequest,
    ReturnRequestItem,
)
from db_inventory.models.site import Room, UserPlacement


class Command(BaseCommand):
    help = "Generate realistic asset return data (bulk optimized)"

    def handle(self, *args, **options):

        self.stdout.write(self.style.WARNING("🧹 Purging return history..."))

        ReturnRequestItem.objects.all().delete()
        ReturnRequest.objects.all().delete()

        self.stdout.write(self.style.SUCCESS("✔ Cleared existing data"))

        DAYS = 730
        today = timezone.now()

        # ----------------------------------
        # Load data
        # ----------------------------------

        user_placements = list(
            UserPlacement.objects.filter(is_current=True).select_related(
                "user",
                "room",
                "room__location",
                "room__location__department",
            )
        )

        if not user_placements:
            self.stdout.write(self.style.ERROR("No users with current locations"))
            return

        rooms = list(Room.objects.all())

        equipment_assignments = list(
            EquipmentAssignment.objects.filter(returned_at__isnull=True)
        )
        accessory_assignments = list(
            AccessoryAssignment.objects.filter(returned_at__isnull=True)
        )
        consumable_issues = list(
            ConsumableIssue.objects.filter(returned_at__isnull=True)
        )

        request_rows = []
        request_items = []

        use_tqdm = sys.stdout.isatty()
        pbar = tqdm(range(DAYS, 0, -1), disable=not use_tqdm)

        # ----------------------------------
        # Generate requests
        # ----------------------------------

        for day_offset in pbar:

            date = today - datetime.timedelta(days=day_offset)

            num_requests = random.randint(5, 20)

            for _ in range(num_requests):

                user_loc = random.choice(user_placements)
                requester = user_loc.user
                user_room = user_loc.room

                requested_at = date + datetime.timedelta(
                    hours=random.randint(8, 18),
                    minutes=random.randint(0, 59),
                )

                days_ago = (today - requested_at).days

                if days_ago > 30:
                    weights = [0.05, 0.3, 0.1, 0.25, 0.3]
                elif days_ago > 7:
                    weights = [0.1, 0.35, 0.1, 0.25, 0.2]
                else:
                    weights = [0.6, 0.2, 0.05, 0.1, 0.05]

                status = random.choices(
                    [
                        ReturnRequest.Status.PENDING,
                        ReturnRequest.Status.APPROVED,
                        ReturnRequest.Status.DENIED,
                        ReturnRequest.Status.PARTIAL,
                        ReturnRequest.Status.COMPLETED,
                    ],
                    weights=weights,
                )[0]

                processed_at = None
                processed_by = None

                if status != ReturnRequest.Status.PENDING:
                    delay_hours = random.randint(2, 72)
                    processed_at = requested_at + datetime.timedelta(hours=delay_hours)
                    processed_by = random.choice([ul.user for ul in user_placements])

                request = ReturnRequest(
                    requester=requester,
                    status=status,
                    requested_at=requested_at,
                    processed_at=processed_at,
                    processed_by=processed_by,
                    notes="Auto-generated realistic return",
                )

                request_rows.append(request)

                # items for this request
                num_items = random.randint(1, 4)

                for _ in range(num_items):

                    item_type = random.choice(
                        [
                            ReturnRequestItem.ItemType.EQUIPMENT,
                            ReturnRequestItem.ItemType.ACCESSORY,
                            ReturnRequestItem.ItemType.CONSUMABLE,
                        ]
                    )

                    room = user_room if random.random() < 0.8 else random.choice(rooms)

                    if status == ReturnRequest.Status.PENDING:
                        item_status = ReturnRequestItem.Status.PENDING
                    elif status == ReturnRequest.Status.COMPLETED:
                        item_status = ReturnRequestItem.Status.APPROVED
                    elif status == ReturnRequest.Status.DENIED:
                        item_status = ReturnRequestItem.Status.DENIED
                    else:
                        item_status = random.choice(
                            [
                                ReturnRequestItem.Status.APPROVED,
                                ReturnRequestItem.Status.DENIED,
                            ]
                        )

                    kwargs = {
                        "item_type": item_type,
                        "room": room,
                        "status": item_status,
                        "verified_by": (
                            processed_by if item_status != "pending" else None
                        ),
                        "verified_at": (
                            processed_at if item_status != "pending" else None
                        ),
                        "notes": "Auto-generated item",
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

                    request_items.append((request, kwargs))

        # ----------------------------------
        # Bulk insert
        # ----------------------------------

        self.stdout.write(self.style.WARNING("Writing requests to database..."))

        with transaction.atomic():

            ReturnRequest.objects.bulk_create(request_rows, batch_size=1000)

            item_rows = []

            for request, kwargs in request_items:
                item_rows.append(
                    ReturnRequestItem(
                        return_request=request,
                        **kwargs,
                    )
                )

            ReturnRequestItem.objects.bulk_create(item_rows, batch_size=2000)

        self.stdout.write(
            self.style.SUCCESS(
                f"Generated {len(request_rows):,} return requests "
                f"and {len(item_rows):,} items 🎉"
            )
        )