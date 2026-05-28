
from django.db import transaction
from django.utils import timezone

from agreements.models.agreements import (
    AssetAgreement,
    AgreementHistory,
)


class AgreementLifecycleService:

    @staticmethod
    @transaction.atomic
    def expire_agreement(
        agreement,
        user=None,
    ):

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
            new_status=AssetAgreement.Status.EXPIRED,
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

