from rest_framework import viewsets
from rest_framework.response import Response
from agreements.api.serialziers.agreement_coverage import AgreementCoverageSerializer, AgreementCoverageWriteSerializer
from agreements.models.agreements import AgreementCoverage
from core.mixins import AuditMixin, ScopeFilterMixin
from core.pagination import FlexiblePagination
from core.models.audit import AuditLog
from rest_framework import status
from authorization.permissions.agreements import AgreementCoveragePermission



class AgreementCoverageViewSet(AuditMixin, ScopeFilterMixin, viewsets.ModelViewSet, ):

    queryset = (
        AgreementCoverage.objects
        .select_related(
            "agreement",
            "department",
            "location",
            "room",
        )
        .order_by("id")
    )

    permission_classes = [AgreementCoveragePermission]

    pagination_class = FlexiblePagination

    lookup_field = "public_id"

    def get_serializer_class(self):
        if self.action in [
            "create",
            "update",
            "partial_update",
        ]:
            return AgreementCoverageWriteSerializer
        return AgreementCoverageSerializer
    
       # -------------------------
    # Create
    # -------------------------

    def create(self, request, *args, **kwargs):

        serializer = self.get_serializer(
            data=request.data,
            context={
                "request": request
            },
        )

        serializer.is_valid(
            raise_exception=True
        )

        coverage = serializer.save()

        # --------------------------------
        # Resolve Scope Label
        # --------------------------------

        scope_target = (
            coverage.department
            or coverage.location
            or coverage.room
            or "GLOBAL"
        )

        # --------------------------------
        # Audit Log
        # --------------------------------

        self.audit(
            AuditLog.Events.AGREEMENT_COVERAGE_CREATED,
            target=coverage,
            description=(
                f"{request.user.email} added "
                f"{coverage.scope_type} coverage "
                f"to agreement "
                f"{coverage.agreement.public_id}"
            ),
            metadata={
                "agreement_public_id":
                    coverage.agreement.public_id,

                "agreement_name":
                    coverage.agreement.name,

                "coverage_public_id":
                    coverage.public_id,

                "scope_type":
                    coverage.scope_type,

                "scope_target":
                    str(scope_target),

                "performed_by":
                    request.user.email,
            },
        )

        response_serializer = (
            AgreementCoverageSerializer(
                coverage,
                context={
                    "request": request
                },
            )
        )

        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED,
        )

    # -------------------------
    # Destroy
    # -------------------------

    def destroy( self, request, *args, **kwargs, ):

        coverage = self.get_object()

        scope_target = (
            coverage.department
            or coverage.location
            or coverage.room
            or "GLOBAL"
        )

        # --------------------------------
        # Audit Log
        # --------------------------------

        self.audit(
            AuditLog.Events.AGREEMENT_COVERAGE_REMOVED,
            target=coverage,
            description=(
                f"{request.user.email} removed "
                f"{coverage.scope_type} coverage "
                f"from agreement "
                f"{coverage.agreement.public_id}"
            ),
            metadata={
                "agreement_public_id":
                    coverage.agreement.public_id,
                "agreement_name":
                    coverage.agreement.name,
                "coverage_public_id":
                    coverage.public_id,
                "scope_type":
                    coverage.scope_type,
                "scope_target":
                    str(scope_target),
                "performed_by":
                    request.user.email,
            },
        )

        coverage.delete()

        return Response(
            status=status.HTTP_204_NO_CONTENT,
        )