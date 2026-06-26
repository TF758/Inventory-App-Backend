
from assignments.models.asset_assignment import AccessoryAssignment, ConsumableIssue
from django.core.exceptions import ValidationError

class AssetUsageService:

    @staticmethod
    def ensure_user_can_use_accessory(
        *,
        user,
        accessory,
        quantity,
    ):
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
                "Usage quantity exceeds your assigned quantity."
            )

        return assignment

    @staticmethod
    def ensure_user_can_use_consumable(
        *,
        user,
        consumable,
        quantity,
    ):
        issue = (
            ConsumableIssue.objects
            .select_for_update()
            .filter(
                consumable=consumable,
                user=user,
                returned_at__isnull=True,
            )
            .first()
        )

        if not issue:
            raise ValidationError(
                "You do not have an active consumable issue for this consumable."
            )

        if quantity > issue.quantity:
            raise ValidationError(
                "Usage quantity exceeds your issued consumable quantity."
            )

        return issue