from rest_framework import status
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from agreements.models.agreements import (
    AssetAgreement,
)
from core.mixins import ( AuditMixin, ScopeFilterMixin, )
from agreements.service import AgreementLifecycleService
from core.models.audit import AuditLog
from agreements.api.serialziers.agreement_lifecycle import ExtendAgreementSerializer, RenewAgreementSerializer
from access.permissions.agreements import AssetAgreementPermission



class AgreementLifecycleViewSet( AuditMixin, ScopeFilterMixin, viewsets.GenericViewSet, ):

    queryset = (
        AssetAgreement.objects
        .select_related(
            "managing_department",
        )
        .order_by("id")
    )

    permission_classes = [AssetAgreementPermission]

    lookup_field = "public_id"

    # -------------------------
    # Terminate
    # -------------------------

    @action( detail=True, methods=["post"], )
    def terminate( self, request, public_id=None, ):
        agreement = self.get_object()

        previous_status = ( agreement.status )

        AgreementLifecycleService.terminate_agreement( agreement=agreement, user=request.user, )

        self.audit(
            AuditLog.Events.AGREEMENT_TERMINATED,
            target=agreement,
            description=(
                f"{request.user.email} "
                f"terminated agreement "
                f"{agreement.public_id}"
            ),
            metadata={
                "agreement_public_id":
                    agreement.public_id,
                "agreement_name":
                    agreement.name,
                "previous_status":
                    previous_status,
                "new_status":
                    agreement.status,
                "performed_by":
                    request.user.email,
            },
        )

        return Response(
            {
                "detail":
                    "Agreement terminated."
            },
            status=status.HTTP_200_OK,
        )
    

    @action( detail=True, methods=["post"], )
    def extend( self, request, public_id=None, ):

        agreement = self.get_object()
        previous_expiry_date = agreement.expiry_date

        serializer = ( ExtendAgreementSerializer( data=request.data ) )


        serializer.is_valid( raise_exception=True )

        agreement = (
            AgreementLifecycleService
            .extend_agreement(
                agreement=agreement,
                new_expiry_date=(
                    serializer
                    .validated_data[
                        "new_expiry_date"
                    ]
                ),
                user=request.user,
                reason=(
                    serializer
                    .validated_data
                    .get("reason", "")
                ),
            )
        )
        self.audit(
            AuditLog.Events.AGREEMENT_EXTENDED,
            target=agreement,
            description=(
                f"{request.user.email} "
                f"extended agreement "
                f"{agreement.public_id}"
            ),
            metadata={
                "agreement_public_id":
                    agreement.public_id,

                "agreement_name":
                    agreement.name,

                "new_expiry_date":
                    str(agreement.expiry_date),

                "previous_expiry_date":
                    str(previous_expiry_date),

                "performed_by":
                    request.user.email,
            },
        )

        return Response(
            {
                "detail":
                    "Agreement extended."
            },
            status=status.HTTP_200_OK,
        )
    

    @action( detail=True, methods=["post"], )
    def renew( self, request, public_id=None, ):

        agreement = self.get_object()

        serializer = (
            RenewAgreementSerializer(
                data=request.data
            )
        )


        serializer.is_valid( raise_exception=True )
        previous_expiry_date = ( agreement.expiry_date )
        previous_renewal_date = ( agreement.renewal_date )

        agreement = (
            AgreementLifecycleService
            .renew_agreement(
                agreement=agreement,
                new_expiry_date=(
                    serializer
                    .validated_data[
                        "new_expiry_date"
                    ]
                ),
                new_renewal_date=(
                    serializer
                    .validated_data.get(
                        "new_renewal_date"
                    )
                ),
                user=request.user,
                reason=(
                    serializer
                    .validated_data.get(
                        "reason",
                        "",
                    )
                ),
            )
        )

        self.audit(
            AuditLog.Events.AGREEMENT_RENEWED,
            target=agreement,
            description=(
                f"{request.user.email} "
                f"renewed agreement "
                f"{agreement.public_id}"
            ),
            metadata={
                "agreement_public_id":
                    agreement.public_id,
                "agreement_name":
                    agreement.name,
                "previous_expiry_date":
                    str(
                        previous_expiry_date
                    ),
                "new_expiry_date":
                    str(
                        agreement.expiry_date
                    ),
                "previous_renewal_date":
                    str(
                        previous_renewal_date
                    ),
                "new_renewal_date":
                    str(
                        agreement.renewal_date
                    ),

                "performed_by":
                    request.user.email,
            },
        )

        return Response(
            {
                "detail":
                    "Agreement renewed."
            },
            status=status.HTTP_200_OK,
        )