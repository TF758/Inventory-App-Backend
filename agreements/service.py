
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from agreements.models.agreements import ( AgreementStatus, AssetAgreement, AgreementHistory, AssetAgreementItem, )
from assets.models.assets import Accessory, Consumable, Equipment
from django.utils import timezone

class AgreementLifecycleService:

    @staticmethod
    @transaction.atomic
    def expire_agreement( agreement, user=None, ):

        if agreement.status == "EXPIRED":
            return False

        previous_status = agreement.status

        agreement.status = "EXPIRED"

        agreement.save(
            update_fields=["status"]
        )

        AgreementHistory.objects.create(
            agreement=agreement,
            event_type=AgreementHistory.EventType.EXPIRED,
            previous_status=previous_status,
            new_status=AgreementStatus.EXPIRED,
            previous_expiry_date=agreement.expiry_date,
            new_expiry_date=agreement.expiry_date,
            previous_renewal_date=agreement.renewal_date,
            new_renewal_date=agreement.renewal_date,
            notes=(
                "Agreement automatically "
                "expired by lifecycle task."
            ),
            user=user,
            user_email=(
                user.email
                if user
                else ""
            ),
        )

        return True

    @staticmethod
    def sync_expired_agreements():

        today = timezone.now().date()

        queryset = (
            AssetAgreement.objects.filter(
                status="ACTIVE",
                expiry_date__isnull=False,
                expiry_date__lt=today,
            )
        )

        expired_count = 0

        for agreement in queryset.iterator():

            changed = (
                AgreementLifecycleService
                .expire_agreement(
                    agreement=agreement
                )
            )

            if changed:
                expired_count += 1

        return expired_count
    
    @staticmethod
    @transaction.atomic
    def terminate_agreement( agreement, user=None, ):

        if ( agreement.status == AgreementStatus.TERMINATED ):
            raise ValidationError( "Agreement is already terminated." )

        previous_status = ( agreement.status )

        agreement.status = (
            AgreementStatus.TERMINATED
        )

        agreement.save(
            update_fields=[
                "status",
            ]
        )

        AgreementHistory.objects.create(
            agreement=agreement,
            event_type=(
                AgreementHistory
                .EventType
                .TERMINATED
            ),
            previous_status=previous_status,
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
            notes=(
                "Agreement terminated."
            ),
            user=user,
            user_email=(
                user.email
                if user
                else ""
            ),
        )

        return True
    

    @staticmethod
    @transaction.atomic
    def extend_agreement( agreement, new_expiry_date, user=None, reason="", ):

        if ( agreement.status == AgreementStatus.TERMINATED ):
            raise ValidationError(
                "Terminated agreements cannot be extended."
            )

        if not agreement.expiry_date:

            raise ValidationError(
                "Agreement has no expiry date to extend."
            )
        
        if agreement.status == AgreementStatus.EXPIRED:
            raise ValidationError(
                "Expired agreements must be renewed rather than extended."
            )

        if new_expiry_date <= agreement.expiry_date:

            raise ValidationError(
                "New expiry date must be later than the current expiry date."
            )

        previous_expiry_date = ( agreement.expiry_date )
        agreement.expiry_date = ( new_expiry_date )
        agreement.save(
            update_fields=[
                "expiry_date",
            ]
        )

        AgreementHistory.objects.create(
            agreement=agreement,
            event_type=(
                AgreementHistory
                .EventType
                .EXTENDED
            ),
            previous_status=agreement.status,
            new_status=agreement.status,
            previous_expiry_date=(
                previous_expiry_date
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
            notes=(
                reason
                or
                "Agreement extended."
            ),
            user=user,
            user_email=(
                user.email
                if user
                else ""
            ),
        )

        return agreement


    @staticmethod
    @transaction.atomic
    def renew_agreement( agreement, new_expiry_date, new_renewal_date=None, user=None, reason="", ):

        previous_expiry_date = ( agreement.expiry_date )

        previous_renewal_date = ( agreement.renewal_date )

        previous_status = ( agreement.status )

        if not new_renewal_date:
            raise ValidationError(
                "Renewal date is required."
            )

        # Cannot renew terminated agreements
        if agreement.status == AgreementStatus.TERMINATED:
            raise ValidationError(
                "Terminated agreements cannot be renewed."
            )

        # New expiry must be later than current expiry
        if (
            previous_expiry_date
            and
            new_expiry_date <= previous_expiry_date
        ):
            raise ValidationError(
                (
                    "Renewal expiry date "
                    "must be later than "
                    "the current expiry date."
                )
            )

        # Renewal date cannot be in the past
        if (
            new_renewal_date
            and
            new_renewal_date < timezone.localdate()
        ):
            raise ValidationError(
                "Renewal date cannot be earlier than today."
            )

        # Renewal date must be before expiry date
        if (
            new_renewal_date
            and
            new_renewal_date >= new_expiry_date
        ):
            raise ValidationError(
                "Renewal date must be before expiry date."
            )
        agreement.expiry_date = (
            new_expiry_date
        )

        agreement.renewal_date = (
            new_renewal_date
        )

        if (
            agreement.status
            == AgreementStatus.EXPIRED
        ):
            agreement.status = (
                AgreementStatus.ACTIVE
            )

        agreement.save(
            update_fields=[
                "expiry_date",
                "renewal_date",
                "status",
            ]
        )

        AgreementHistory.objects.create(
            agreement=agreement,
            event_type=(
                AgreementHistory
                .EventType
                .RENEWED
            ),
            previous_status=(
                previous_status
            ),
            new_status=(
                agreement.status
            ),
            previous_expiry_date=(
                previous_expiry_date
            ),
            new_expiry_date=(
                agreement.expiry_date
            ),
            previous_renewal_date=(
                previous_renewal_date
            ),
            new_renewal_date=(
                agreement.renewal_date
            ),
            notes=(
                reason
                or
                "Agreement renewed."
            ),
            user=user,
            user_email=(
                user.email
                if user
                else ""
            ),
        )

        return agreement



def is_asset_already_attached(
    agreement: AssetAgreement,
    asset,
) -> bool:
    """
    Returns True if the asset is already
    attached to the agreement.
    """

    if isinstance(asset, Equipment):
        return AssetAgreementItem.objects.filter(
            agreement=agreement,
            equipment=asset,
        ).exists()

    if isinstance(asset, Accessory):
        return AssetAgreementItem.objects.filter(
            agreement=agreement,
            accessory=asset,
        ).exists()

    if isinstance(asset, Consumable):
        return AssetAgreementItem.objects.filter(
            agreement=agreement,
            consumable=asset,
        ).exists()

    return False

def get_attached_agreement_ids(asset):
    """
    Returns agreement ids already attached
    to the supplied asset.
    """

    if isinstance(asset, Equipment):
        return AssetAgreementItem.objects.filter(
            equipment=asset,
        ).values_list(
            "agreement_id",
            flat=True,
        )

    if isinstance(asset, Accessory):
        return AssetAgreementItem.objects.filter(
            accessory=asset,
        ).values_list(
            "agreement_id",
            flat=True,
        )

    if isinstance(asset, Consumable):
        return AssetAgreementItem.objects.filter(
            consumable=asset,
        ).values_list(
            "agreement_id",
            flat=True,
        )

    return AssetAgreement.objects.none()