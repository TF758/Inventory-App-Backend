from agreements.models.agreements import (
    AgreementCoverage,
    CoverageScopeType,
)
from sites.models.sites import Room, UserPlacement

def resolve_room_hierarchy( room: Room, ):
    """
    Resolves the full organizational
    hierarchy for a room.
    """

    return {
        "room": room,

        "location":
            room.location
            if room and room.location
            else None,

        "department":
            room.location.department
            if room and room.location
            else None
    }

def agreement_covers_room(
    agreement,
    room,
) -> bool:
    """
    Determines whether an agreement
    applies to a given room based on
    its coverage rules.
    """

    if not room:
        return False

    hierarchy = resolve_room_hierarchy(
        room
    )

    coverages = (
        agreement.coverages.all()
    )

    for coverage in coverages:

        # -------------------------
        # GLOBAL
        # -------------------------

        if (
            coverage.scope_type
            == CoverageScopeType.GLOBAL
        ):
            return True

        # -------------------------
        # ROOM
        # -------------------------

        if (
            coverage.scope_type
            == CoverageScopeType.ROOM
            and
            coverage.room
            == hierarchy["room"]
        ):
            return True

        # -------------------------
        # LOCATION
        # -------------------------

        if (
            coverage.scope_type
            == CoverageScopeType.LOCATION
            and
            coverage.location
            == hierarchy["location"]
        ):
            return True

        # -------------------------
        # DEPARTMENT
        # -------------------------

        if (
            coverage.scope_type
            == CoverageScopeType.DEPARTMENT
            and
            coverage.department
            == hierarchy["department"]
        ):
            return True

    return False

def can_attach_asset_to_agreement(
    agreement,
    asset,
) -> bool:
    """
    Determines whether an asset
    may be attached to an agreement.
    """

    room = getattr(
        asset,
        "room",
        None,
    )

    return agreement_covers_room(
        agreement,
        room,
    )

def can_attach_user_to_agreement(
    agreement,
    user,
) -> bool:
    """
    Determines whether a user
    may be attached to an agreement
    based on current placement.
    """

    placement = (
        UserPlacement.objects
        .filter(
            user=user,
            is_current=True,
        )
        .select_related(
            "room__location__department"
        )
        .first()
    )

    if not placement:
        return False

    return agreement_covers_room(
        agreement,
        placement.room,
    )