from django.core.exceptions import ValidationError
from assignments.models.asset_assignment import AccessoryAssignment
from core.permissions.helpers import get_active_role, is_admin_role


class SelfReturnService:

    @staticmethod
    def ensure_can_self_return_accessory(
        *,
        user,
        accessory,
        quantity,
    ):
        active_role = get_active_role(user)

        if active_role and is_admin_role(active_role.role):
            raise ValidationError(
                "Administrators must use the administrative return workflow."
            )

        assignment = (
            AccessoryAssignment.objects
            .select_for_update()
            .filter(
                accessory=accessory,
                user=user,
                returned_at__isnull=True,
            )
            .first()
        )

        if not assignment:
            raise ValidationError(
                "You do not have an active assignment for this accessory."
            )

        if quantity > assignment.quantity:
            raise ValidationError(
                "Return exceeds assigned quantity."
            )

        return assignment