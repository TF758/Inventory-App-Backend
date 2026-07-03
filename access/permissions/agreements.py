from access.permissions.scoped import ( ScopedPermission )
from access.services.scope import ( ScopeService )
from agreements.models.agreements import ( AssetAgreement, AssetAgreementItem )

class AssetAgreementPermission(ScopedPermission):
    """
    Authorization for all agreement-related endpoints.
    """

    permission_map = {
        "GET": "agreements.view",
        "POST": "agreements.create",
        "PUT": "agreements.update",
        "PATCH": "agreements.update",
        "DELETE": "agreements.delete",
    }

    CUSTOM_PERMISSION_MAP = {
        # AssetAgreementItemViewSet
        "attach": "agreements.attach_items",
        "detach": "agreements.detach_items",

        # AgreementLifecycleViewSet
        "extend": "agreements.extend",
        "renew": "agreements.renew",
        "terminate": "agreements.terminate",
    }

    def get_required_permissions(
        self,
        request,
        view,
    ):
        permission = self.CUSTOM_PERMISSION_MAP.get(
            getattr(view, "action", None),
        )

        if permission:
            return [permission]

        return super().get_required_permissions(
            request,
            view,
        )

    def has_object_permission(
        self,
        request,
        view,
        obj,
    ):
        active_role = getattr(
            request.user,
            "active_role",
            None,
        )

        if not active_role:
            return False

        if isinstance(
            obj,
            AssetAgreementItem,
        ):
            agreement = obj.agreement

        elif isinstance(
            obj,
            AssetAgreement,
        ):
            agreement = obj

        else:
            agreement = getattr(
                obj,
                "agreement",
                None,
            )

        if not agreement:
            return False

        return (
            self.has_permission(
                request,
                view,
            )
            and ScopeService.can_access_room(
                active_role,
                agreement.room,
            )
        )