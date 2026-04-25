from datetime import timedelta

from django.db.models import Count, F, Q, Sum
from django.utils import timezone

from analytics.services.snapshots import User
from assets.models.assets import Accessory, Consumable, Equipment
from assignments.models.asset_assignment import AccessoryAssignment, AccessoryEvent, ConsumableIssue
from sites.models.sites import Department, Location, Room, UserPlacement
from users.models.roles import RoleAssignment


def resolve_inventory_scope(scope: str, scope_id: str | None) -> dict:
    """
    Resolve report scope into reusable querysets.

    Returns:
    {
        "scope_name": str,
        "departments": queryset,
        "locations": queryset,
        "rooms": queryset,
    }
    """

    departments = Department.objects.none()
    locations = Location.objects.none()
    rooms = Room.objects.none()

    scope_name = "Entire Site"

    # -----------------------------------------
    # Global
    # -----------------------------------------
    if scope == "global":
        departments = Department.objects.all()
        locations = Location.objects.all()
        rooms = Room.objects.all()

    # -----------------------------------------
    # Department
    # -----------------------------------------
    elif scope == "department":
        department = Department.objects.get(
            public_id__iexact=scope_id
        )

        departments = Department.objects.filter(
            id=department.id
        )

        locations = Location.objects.filter(
            department=department
        )

        rooms = Room.objects.filter(
            location__department=department
        )

        scope_name = department.name

    # -----------------------------------------
    # Location
    # -----------------------------------------
    elif scope == "location":
        location = Location.objects.select_related(
            "department"
        ).get(
            public_id__iexact=scope_id
        )

        departments = Department.objects.filter(
            id=location.department_id
        )

        locations = Location.objects.filter(
            id=location.id
        )

        rooms = Room.objects.filter(
            location=location
        )

        scope_name = location.name

    # -----------------------------------------
    # Room
    # -----------------------------------------
    elif scope == "room":
        room = Room.objects.select_related(
            "location",
            "location__department",
        ).get(
            public_id__iexact=scope_id
        )

        departments = Department.objects.filter(
            id=room.location.department_id
        )

        locations = Location.objects.filter(
            id=room.location_id
        )

        rooms = Room.objects.filter(
            id=room.id
        )

        scope_name = room.name

    else:
        raise ValueError("Invalid scope.")

    return {
        "scope_name": scope_name,
        "departments": departments,
        "locations": locations,
        "rooms": rooms,
    }


def build_inventory_summary_report(
    *,
    scope: str,
    scope_id: str | None,
    generated_by=None,
) -> dict:
    """
    Canonical payload:

    {
        "meta": {},
        "data": {}
    }
    """

    now = timezone.now()
    thirty_days_ago = now - timedelta(days=30)

    # =====================================================
    # Scope Resolver
    # =====================================================
    resolved = resolve_inventory_scope(
        scope=scope,
        scope_id=scope_id,
    )

    scope_name = resolved["scope_name"]
    departments = resolved["departments"]
    locations = resolved["locations"]
    rooms = resolved["rooms"]

    room_ids = rooms.values_list("id", flat=True)

    # =====================================================
    # Base Querysets
    # =====================================================
    equipment_qs = Equipment.objects.filter(
        room_id__in=room_ids,
        is_deleted=False,
    )

    accessory_qs = Accessory.objects.filter(
        room_id__in=room_ids,
        is_deleted=False,
    )

    consumable_qs = Consumable.objects.filter(
        room_id__in=room_ids,
        is_deleted=False,
    )

    placements = UserPlacement.objects.filter(
        room_id__in=room_ids,
        is_current=True,
    )

    users_qs = User.objects.filter(
        id__in=placements.values("user_id")
    ).distinct()

    # =====================================================
    # Overview KPIs
    # =====================================================
    usable_equipment = equipment_qs.exclude(
        status__in=["retired", "condemned"]
    )

    assigned_equipment = usable_equipment.filter(
        active_assignment__returned_at__isnull=True
    ).distinct()

    usable_count = usable_equipment.count()
    assigned_count = assigned_equipment.count()

    equipment_utilization = (
        round((assigned_count / usable_count) * 100, 2)
        if usable_count else 0
    )

    total_equipment = equipment_qs.count()

    total_accessories = (
        accessory_qs.aggregate(
            total=Sum("quantity")
        )["total"] or 0
    )

    total_consumables = (
        consumable_qs.aggregate(
            total=Sum("quantity")
        )["total"] or 0
    )

    low_stock_count = consumable_qs.filter(
        low_stock_threshold__gt=0,
        quantity__lte=F("low_stock_threshold"),
    ).count()

    overview = {
        "total_equipment": total_equipment,
        "total_accessories_units": total_accessories,
        "total_consumables_units": total_consumables,
        "total_users": users_qs.count(),
        "equipment_utilization_percent":
            equipment_utilization,
        "floating_equipment":
            usable_count - assigned_count,
        "low_stock_consumables":
            low_stock_count,
        "damaged_assets":
            equipment_qs.filter(
                status="damaged"
            ).count(),
        "lost_assets":
            equipment_qs.filter(
                status="lost"
            ).count(),
    }

    # =====================================================
    # Scope Summary
    # =====================================================
    scope_summary = {
        "scope": scope,
        "scope_name": scope_name,
        "departments": departments.count(),
        "locations": locations.count(),
        "rooms": rooms.count(),
        "users": users_qs.count(),
    }

    # =====================================================
    # Equipment Summary
    # =====================================================
    equipment = {
        "total": total_equipment,
        "usable": usable_count,
        "assigned": assigned_count,
        "unassigned": usable_count - assigned_count,
        "ok":
            equipment_qs.filter(
                status="ok"
            ).count(),
        "damaged":
            equipment_qs.filter(
                status="damaged"
            ).count(),
        "under_repair":
            equipment_qs.filter(
                status="under_repair"
            ).count(),
        "lost":
            equipment_qs.filter(
                status="lost"
            ).count(),
        "retired":
            equipment_qs.filter(
                status="retired"
            ).count(),
        "condemned":
            equipment_qs.filter(
                status="condemned"
            ).count(),
        "utilization_percent":
            equipment_utilization,
    }

    # =====================================================
    # Accessory Summary
    # =====================================================
    assigned_accessories = (
        AccessoryAssignment.objects.filter(
            accessory__in=accessory_qs,
            returned_at__isnull=True,
        ).aggregate(
            total=Sum("quantity")
        )["total"] or 0
    )

    accessories = {
        "total_units": total_accessories,
        "assigned_units": assigned_accessories,
        "available_units":
            total_accessories -
            assigned_accessories,
        "utilization_percent": (
            round(
                (
                    assigned_accessories /
                    total_accessories
                ) * 100,
                2,
            )
            if total_accessories else 0
        ),
        "damage_events_last_30_days":
            AccessoryEvent.objects.filter(
                accessory__in=accessory_qs,
                event_type="damaged",
                occurred_at__gte=thirty_days_ago,
            ).count(),
        "lost_units": (
            AccessoryEvent.objects.filter(
                accessory__in=accessory_qs,
                event_type="lost",
            ).aggregate(
                total=Sum("quantity")
            )["total"] or 0
        ),
    }

    # =====================================================
    # Consumable Summary
    # =====================================================
    active_issued = (
        ConsumableIssue.objects.filter(
            consumable__in=consumable_qs,
            returned_at__isnull=True,
        ).aggregate(
            total=Sum("quantity")
        )["total"] or 0
    )

    consumables = {
        "total_units_in_stock":
            total_consumables,
        "active_issued_quantity":
            active_issued,
        "available_quantity":
            total_consumables,
        "low_stock_items":
            low_stock_count,
        "out_of_stock_items":
            consumable_qs.filter(
                quantity=0
            ).count(),
    }

    # =====================================================
    # User Summary
    # =====================================================
    users = {
        "total": users_qs.count(),
        "active":
            users_qs.filter(
                is_active=True
            ).count(),
        "inactive":
            users_qs.filter(
                is_active=False
            ).count(),
        "locked":
            users_qs.filter(
                is_locked=True
            ).count(),
    }

    # =====================================================
    # Role Distribution
    # =====================================================
    role_qs = RoleAssignment.objects.none()

    if scope == "global":
        role_qs = RoleAssignment.objects.all()

    elif scope == "department":
        role_qs = RoleAssignment.objects.filter(
            Q(department__in=departments) |
            Q(location__department__in=departments) |
            Q(room__location__department__in=departments)
        ).exclude(
            role="SITE_ADMIN"
        )

    elif scope == "location":
        role_qs = RoleAssignment.objects.filter(
            Q(location__in=locations) |
            Q(room__location__in=locations)
        ).exclude(
            role__in=[
                "SITE_ADMIN",
                "DEPARTMENT_ADMIN",
                "DEPARTMENT_VIEWER",
            ]
        )

    elif scope == "room":
        role_qs = RoleAssignment.objects.filter(
            room__in=rooms
        ).exclude(
            role__in=[
                "SITE_ADMIN",
                "DEPARTMENT_ADMIN",
                "DEPARTMENT_VIEWER",
                "LOCATION_ADMIN",
                "LOCATION_VIEWER",
            ]
        )

    roles = {
        row["role"]: row["count"]
        for row in role_qs.values(
            "role"
        ).annotate(
            count=Count("id")
        )
    }

    # =====================================================
    # Breakdown
    # =====================================================
    breakdown = []

    if scope == "global":
        for dept in departments:
            ids = Room.objects.filter(
                location__department=dept
            ).values_list(
                "id",
                flat=True,
            )

            eq = Equipment.objects.filter(
                room_id__in=ids,
                is_deleted=False,
            )

            us = UserPlacement.objects.filter(
                room_id__in=ids,
                is_current=True,
            )

            breakdown.append({
                "scope_type": "department",
                "scope_name": dept.name,
                "equipment": eq.count(),
                "assigned_equipment":
                    eq.filter(
                        active_assignment__returned_at__isnull=True
                    ).count(),
                "damaged_equipment":
                    eq.filter(
                        status="damaged"
                    ).count(),
                "under_repair":
                    eq.filter(
                        status="under_repair"
                    ).count(),
                "accessory_units":
                    Accessory.objects.filter(
                        room_id__in=ids,
                        is_deleted=False,
                    ).aggregate(
                        total=Sum("quantity")
                    )["total"] or 0,
                "consumable_units":
                    Consumable.objects.filter(
                        room_id__in=ids,
                        is_deleted=False,
                    ).aggregate(
                        total=Sum("quantity")
                    )["total"] or 0,
                "low_stock_consumables":
                    Consumable.objects.filter(
                        room_id__in=ids,
                        is_deleted=False,
                        low_stock_threshold__gt=0,
                        quantity__lte=F(
                            "low_stock_threshold"
                        ),
                    ).count(),
                "users":
                    us.count(),
                "active_users":
                    User.objects.filter(
                        id__in=us.values("user_id"),
                        is_active=True,
                    ).count(),
            })

    elif scope == "department":
        for loc in locations:
            ids = Room.objects.filter(
                location=loc
            ).values_list(
                "id",
                flat=True,
            )

            eq = Equipment.objects.filter(
                room_id__in=ids,
                is_deleted=False,
            )

            us = UserPlacement.objects.filter(
                room_id__in=ids,
                is_current=True,
            )

            breakdown.append({
                "scope_type": "location",
                "scope_name": loc.name,
                "equipment": eq.count(),
                "assigned_equipment":
                    eq.filter(
                        active_assignment__returned_at__isnull=True
                    ).count(),
                "damaged_equipment":
                    eq.filter(
                        status="damaged"
                    ).count(),
                "under_repair":
                    eq.filter(
                        status="under_repair"
                    ).count(),
                "accessory_units":
                    Accessory.objects.filter(
                        room_id__in=ids,
                        is_deleted=False,
                    ).aggregate(
                        total=Sum("quantity")
                    )["total"] or 0,
                "consumable_units":
                    Consumable.objects.filter(
                        room_id__in=ids,
                        is_deleted=False,
                    ).aggregate(
                        total=Sum("quantity")
                    )["total"] or 0,
                "low_stock_consumables":
                    Consumable.objects.filter(
                        room_id__in=ids,
                        is_deleted=False,
                        low_stock_threshold__gt=0,
                        quantity__lte=F(
                            "low_stock_threshold"
                        ),
                    ).count(),
                "users":
                    us.count(),
                "active_users":
                    User.objects.filter(
                        id__in=us.values("user_id"),
                        is_active=True,
                    ).count(),
            })

    elif scope == "location":
        for rm in rooms:
            eq = Equipment.objects.filter(
                room=rm,
                is_deleted=False,
            )

            us = UserPlacement.objects.filter(
                room=rm,
                is_current=True,
            )

            breakdown.append({
                "scope_type": "room",
                "scope_name": rm.name,
                "equipment": eq.count(),
                "assigned_equipment":
                    eq.filter(
                        active_assignment__returned_at__isnull=True
                    ).count(),
                "damaged_equipment":
                    eq.filter(
                        status="damaged"
                    ).count(),
                "under_repair":
                    eq.filter(
                        status="under_repair"
                    ).count(),
                "accessory_units":
                    Accessory.objects.filter(
                        room=rm,
                        is_deleted=False,
                    ).aggregate(
                        total=Sum("quantity")
                    )["total"] or 0,
                "consumable_units":
                    Consumable.objects.filter(
                        room=rm,
                        is_deleted=False,
                    ).aggregate(
                        total=Sum("quantity")
                    )["total"] or 0,
                "low_stock_consumables":
                    Consumable.objects.filter(
                        room=rm,
                        is_deleted=False,
                        low_stock_threshold__gt=0,
                        quantity__lte=F(
                            "low_stock_threshold"
                        ),
                    ).count(),
                "users":
                    us.count(),
                "active_users":
                    User.objects.filter(
                        id__in=us.values("user_id"),
                        is_active=True,
                    ).count(),
            })

    # =====================================================
    # Final Payload
    # =====================================================
    return {
        "meta": {
            "report_name":
                "Inventory Summary Report",
            "generated_at":
                now.isoformat(),
            "generated_by":
                str(generated_by)
                if generated_by else None,
            "scope": scope,
            "scope_id": scope_id,
            "scope_name": scope_name,
        },
        "data": {
            "overview": overview,
            "scope_summary": scope_summary,
            "equipment": equipment,
            "accessories": accessories,
            "consumables": consumables,
            "users": users,
            "roles": roles,
            "breakdown": breakdown,
        },
    }