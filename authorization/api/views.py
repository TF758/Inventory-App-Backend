from collections import defaultdict
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.generics import ( GenericAPIView, ListAPIView, RetrieveAPIView, )
from rest_framework.response import Response
from rest_framework.views import APIView
from authorization.models import ( Permission, Role, RolePermission, )
from authorization.api.serialziers import RoleDetailSerializer, RolePermissionUpdateSerializer, RoleSerializer




class RoleListView(ListAPIView):
    """
    GET /api/authorization/roles/
    """

    serializer_class = RoleSerializer

    def get_queryset(self):
        return (
            Role.objects
            .prefetch_related(
                "role_permissions__permission"
            )
            .order_by("level", "name")
        )


class RolePermissionsView(RetrieveAPIView):
    """
    GET /api/authorization/roles/<public_id>/permissions/
    """

    serializer_class = RoleDetailSerializer

    lookup_field = "public_id"
    lookup_url_kwarg = "public_id"

    def get_queryset(self):
        return (
            Role.objects
            .prefetch_related(
                "role_permissions__permission"
            )
            .order_by("level", "name")
        )


class RolePermissionsUpdateView(GenericAPIView):
    """
    PATCH /api/authorization/roles/<public_id>/permissions/
    """

    serializer_class = RolePermissionUpdateSerializer

    @transaction.atomic
    def patch(self, request, public_id):
        role = get_object_or_404(
            Role,
            public_id=public_id,
        )

        serializer = self.get_serializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        permission_codes = serializer.validated_data[
            "permissions"
        ]

        permissions = list(
            Permission.objects.filter(
                code__in=permission_codes
            )
        )

        RolePermission.objects.filter(
            role=role
        ).delete()

        RolePermission.objects.bulk_create(
            [
                RolePermission(
                    role=role,
                    permission=permission,
                    enabled=True,
                )
                for permission in permissions
            ]
        )

        role = (
            Role.objects
            .prefetch_related(
                "role_permissions__permission"
            )
            .get(
                public_id=role.public_id
            )
        )

        return Response(
            RoleDetailSerializer(
                role,
                context={
                    "request": request
                },
            ).data,
            status=status.HTTP_200_OK,
        )


class PermissionMatrixView(APIView):
    """
    GET /api/authorization/matrix/
    """

    def get(self, request):
        roles = list(
            Role.objects.order_by(
                "level",
                "name",
            )
        )

        permissions = list(
            Permission.objects.order_by(
                "module",
                "code",
            )
        )

        mappings = (
            RolePermission.objects
            .filter(enabled=True)
            .values_list(
                "permission_id",
                "role_id",
            )
        )

        permission_role_map = defaultdict(set)

        for permission_id, role_id in mappings:
            permission_role_map[
                permission_id
            ].add(role_id)

        matrix = []

        for permission in permissions:
            assigned_role_ids = permission_role_map.get(
                permission.id,
                set(),
            )

            matrix.append(
                {
                    "public_id": permission.public_id,
                    "code": permission.code,
                    "name": permission.name,
                    "description": permission.description,
                    "module": permission.module,
                    "is_system": permission.is_system,
                    "roles": {
                        role.code: role.id in assigned_role_ids
                        for role in roles
                    },
                }
            )

        return Response(
            {
                "roles": [
                    {
                        "public_id": role.public_id,
                        "code": role.code,
                        "name": role.name,
                        "scope_type": role.scope_type,
                        "level": role.level,
                        "is_system_role": role.is_system_role,
                    }
                    for role in roles
                ],
                "permissions": matrix,
            }
        )