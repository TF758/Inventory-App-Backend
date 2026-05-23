import random
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from tqdm import tqdm

from assets.models.agreements import (
    AssetAgreement,
    AgreementCoverage,
    AssetAgreementItem,
    AgreementHistory,
    AgreementItemHistory,
    CoverageScopeType,
)

from assets.models.assets import (
    Equipment,
    Consumable,
    Accessory,
)

from sites.models.sites import (
    Department,
    Location,
    Room,
)

from users.models.users import User


AGREEMENT_TYPES = [
    "LICENSE",
    "WARRANTY",
    "SERVICE",
    "MAINTENANCE",
    "SUPPORT",
    "OTHER",
]

STATUSES = [
    "ACTIVE",
    "EXPIRED",
    "PENDING",
    "TERMINATED",
]

HISTORY_EVENTS = [
    "CREATED",
    "RENEWED",
    "EXTENDED",
    "TERMINATED",
    "STATUS_CHANGED",
]

ITEM_HISTORY_EVENTS = [
    "ATTACHED",
    "REMOVED",
    "INVALIDATED",
    "REINSTATED",
    "COVERAGE_EXPIRED",
]


class Command(BaseCommand):

    help = "Generate realistic agreement data"

    def handle(self, *args, **kwargs):

        # ----------------------------------
        # Purge Existing
        # ----------------------------------

        self.stdout.write(
            self.style.WARNING(
                "Purging agreement data..."
            )
        )

        with transaction.atomic():

            AgreementItemHistory.objects.all().delete()
            AgreementHistory.objects.all().delete()
            AssetAgreementItem.objects.all().delete()
            AgreementCoverage.objects.all().delete()
            AssetAgreement.objects.all().delete()

        self.stdout.write(
            self.style.SUCCESS(
                "Existing agreement data cleared."
            )
        )

        # ----------------------------------
        # Load Organizational Data
        # ----------------------------------

        self.stdout.write(
            self.style.MIGRATE_HEADING(
                "Loading organizational data..."
            )
        )

        departments = list( Department.objects.all() )
        locations = list( Location.objects.select_related( "department" ) )
        rooms = list( Room.objects.select_related( "location", "location__department", ) )

        equipment = list(
            Equipment.objects.select_related(
                "room",
                "room__location",
                "room__location__department",
            )
        )

        consumables = list(
            Consumable.objects.select_related(
                "room",
                "room__location",
                "room__location__department",
            )
        )

        accessories = list(
            Accessory.objects.select_related(
                "room",
                "room__location",
                "room__location__department",
            )
        )

        users = list(
            User.objects.filter(
                is_active=True
            )
        )

        if not users:
            self.stdout.write(
                self.style.ERROR(
                    "No active users found."
                )
            )
            return

        # ----------------------------------
        # Agreements
        # ----------------------------------

        self.stdout.write(
            self.style.MIGRATE_HEADING(
                "Preparing agreements..."
            )
        )

        agreements = []

        today = timezone.now().date()

        for i in tqdm(
            range(500),
            desc="Generating agreements",
        ):

            start_date = today - timedelta(
                days=random.randint(30, 1200)
            )

            expiry_date = start_date + timedelta(
                days=random.randint(180, 1095)
            )

            status = random.choices(
                STATUSES,
                weights=[0.7, 0.15, 0.1, 0.05],
            )[0]

            agreements.append(
                AssetAgreement(
                    name=f"Agreement {i+1}",
                    agreement_type=random.choice(
                        AGREEMENT_TYPES
                    ),
                    status=status,
                    vendor=f"Vendor {random.randint(1, 100)}",
                    reference_number=(
                        f"REF-{random.randint(10000,99999)}"
                    ),
                    start_date=start_date,
                    expiry_date=expiry_date,
                    renewal_date=(
                        expiry_date - timedelta(days=30)
                    ),
                    auto_renew=random.random() < 0.7,
                    cost=random.randint(500, 50000),
                    currency="USD",
                    managing_department=random.choice(
                        departments
                    ),
                    notes="Synthetic agreement data",
                )
            )

        self.stdout.write(
            self.style.WARNING(
                "Writing agreements..."
            )
        )

        AssetAgreement.objects.bulk_create(
            agreements,
            batch_size=500,
        )

        agreements = list(
            AssetAgreement.objects.all()
        )

        # ----------------------------------
        # Agreement Coverage
        # ----------------------------------

        self.stdout.write(
            self.style.MIGRATE_HEADING(
                "Generating agreement coverages..."
            )
        )

        for agreement in tqdm(
            agreements,
            desc="Generating coverages",
        ):

            coverage_type = random.choices(
                [
                    CoverageScopeType.GLOBAL,
                    CoverageScopeType.DEPARTMENT,
                    CoverageScopeType.LOCATION,
                    CoverageScopeType.ROOM,
                ],
                weights=[0.05, 0.35, 0.35, 0.25],
            )[0]

            try:

                # -------------------------
                # GLOBAL
                # -------------------------

                if (
                    coverage_type
                    == CoverageScopeType.GLOBAL
                ):

                    AgreementCoverage.objects.create(
                        agreement=agreement,
                        scope_type=CoverageScopeType.GLOBAL,
                        notes="Global coverage",
                    )

                    continue

                # -------------------------
                # Department Coverage
                # -------------------------

                if (
                    coverage_type
                    == CoverageScopeType.DEPARTMENT
                ):

                    selected_departments = random.sample(
                        departments,
                        random.randint(1, 3),
                    )

                    for department in selected_departments:

                        try:

                            AgreementCoverage.objects.create(
                                agreement=agreement,
                                scope_type=(
                                    CoverageScopeType.DEPARTMENT
                                ),
                                department=department,
                                notes="Department coverage",
                            )

                        except Exception:
                            continue

                # -------------------------
                # Location Coverage
                # -------------------------

                elif (
                    coverage_type
                    == CoverageScopeType.LOCATION
                ):

                    selected_locations = random.sample(
                        locations,
                        random.randint(1, 5),
                    )

                    for location in selected_locations:

                        try:

                            AgreementCoverage.objects.create(
                                agreement=agreement,
                                scope_type=(
                                    CoverageScopeType.LOCATION
                                ),
                                location=location,
                                notes="Location coverage",
                            )

                        except Exception:
                            continue

                # -------------------------
                # Room Coverage
                # -------------------------

                elif (
                    coverage_type
                    == CoverageScopeType.ROOM
                ):

                    selected_rooms = random.sample(
                        rooms,
                        random.randint(1, 8),
                    )

                    for room in selected_rooms:

                        try:

                            AgreementCoverage.objects.create(
                                agreement=agreement,
                                scope_type=(
                                    CoverageScopeType.ROOM
                                ),
                                room=room,
                                notes="Room coverage",
                            )

                        except Exception:
                            continue

            except Exception:
                continue

        # ----------------------------------
        # Agreement Items
        # ----------------------------------

        self.stdout.write(
            self.style.MIGRATE_HEADING(
                "Preparing agreement items..."
            )
        )

        agreement_items = []

        asset_pool = (
            equipment
            + consumables
            + accessories
        )

        random.shuffle(asset_pool)

        for agreement in tqdm(
            agreements,
            desc="Generating agreement items",
        ):

            item_count = random.randint(5, 25)

            assets = random.sample(
                asset_pool,
                min(item_count, len(asset_pool)),
            )

            for asset in assets:

                try:

                    item = AssetAgreementItem(
                        agreement=agreement,
                    )

                    if isinstance(asset, Equipment):
                        item.equipment = asset

                    elif isinstance(asset, Consumable):
                        item.consumable = asset

                    elif isinstance(asset, Accessory):
                        item.accessory = asset

                    item.full_clean()

                    agreement_items.append(item)

                except Exception:
                    continue

        self.stdout.write(
            self.style.WARNING(
                "Writing agreement items..."
            )
        )

        AssetAgreementItem.objects.bulk_create(
            agreement_items,
            batch_size=1000,
        )

        agreement_items = list(
            AssetAgreementItem.objects.select_related(
                "agreement",
                "equipment",
                "consumable",
                "accessory",
            )
        )

        # ----------------------------------
        # Agreement History
        # ----------------------------------

        self.stdout.write(
            self.style.MIGRATE_HEADING(
                "Preparing agreement history..."
            )
        )

        history_rows = []

        for agreement in tqdm(
            agreements,
            desc="Generating agreement history",
        ):

            history_count = random.randint(1, 5)

            current_date = agreement.start_date

            for _ in range(history_count):

                current_date += timedelta(
                    days=random.randint(30, 180)
                )

                user = random.choice(users)

                history_rows.append(
                    AgreementHistory(
                        agreement=agreement,
                        event_type=random.choice(
                            HISTORY_EVENTS
                        ),
                        previous_status="ACTIVE",
                        new_status=agreement.status,
                        previous_expiry_date=(
                            agreement.expiry_date
                        ),
                        new_expiry_date=(
                            agreement.expiry_date
                        ),
                        previous_renewal_date=(
                            agreement.renewal_date
                        ),
                        new_renewal_date=(
                            agreement.renewal_date
                        ),
                        notes="Synthetic history event",
                        created_at=(
                            timezone.make_aware(
                                timezone.datetime.combine(
                                    current_date,
                                    timezone.datetime.min.time(),
                                )
                            )
                        ),
                        user=user,
                        user_email=user.email,
                    )
                )

        self.stdout.write(
            self.style.WARNING(
                "Writing agreement history..."
            )
        )

        AgreementHistory.objects.bulk_create(
            history_rows,
            batch_size=1000,
        )

        # ----------------------------------
        # Agreement Item History
        # ----------------------------------

        self.stdout.write(
            self.style.MIGRATE_HEADING(
                "Preparing agreement item history..."
            )
        )

        item_history_rows = []

        for item in tqdm(
            agreement_items,
            desc="Generating agreement item history",
        ):

            history_count = random.randint(1, 4)

            current_date = today

            asset = item.asset

            if not asset:
                continue

            for _ in range(history_count):

                current_date += timedelta(
                    days=random.randint(15, 120)
                )

                user = random.choice(users)

                item_history_rows.append(
                    AgreementItemHistory(
                        agreement=item.agreement,
                        agreement_item=item,
                        event_type=random.choice(
                            ITEM_HISTORY_EVENTS
                        ),
                        asset_public_id=(
                            item.asset_public_id_snapshot
                        ),
                        asset_name=(
                            item.asset_name_snapshot
                        ),
                        asset_serial=(
                            item.asset_serial_snapshot
                        ),
                        asset_type=item.asset_type,
                        coverage_start=(
                            item.coverage_start
                        ),
                        coverage_end=(
                            item.coverage_end
                        ),
                       department_name=(
                        asset.room.location.department.name
                        if (
                            asset.room
                            and asset.room.location
                            and asset.room.location.department
                        )
                        else ""
                        ),

                        location_name=(
                        asset.room.location.name
                        if (
                            asset.room
                            and asset.room.location
                        )
                        else ""
                        ),

                        room_name=(
                        asset.room.name
                        if asset.room
                        else ""
                        ),
                        reason=(
                            "Synthetic enrollment history"
                        ),
                        metadata={
                            "generated": True,
                        },
                        created_at=(
                            timezone.make_aware(
                                timezone.datetime.combine(
                                    current_date,
                                    timezone.datetime.min.time(),
                                )
                            )
                        ),
                        user=user,
                        user_email=user.email,
                    )
                )

        self.stdout.write(
            self.style.WARNING(
                "Writing agreement item history..."
            )
        )

        AgreementItemHistory.objects.bulk_create(
            item_history_rows,
            batch_size=1000,
        )

        # ----------------------------------
        # Complete
        # ----------------------------------

        self.stdout.write(
            self.style.SUCCESS(
                "\nAgreement generation complete 🎉\n"
                f"- Agreements: {len(agreements):,}\n"
                f"- Agreement Items: {len(agreement_items):,}\n"
                f"- Agreement History: {len(history_rows):,}\n"
                f"- Agreement Item History: "
                f"{len(item_history_rows):,}\n"
            )
        )