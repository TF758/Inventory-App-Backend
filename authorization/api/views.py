from collections import defaultdict
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.generics import ( GenericAPIView, ListAPIView, RetrieveAPIView, )
from rest_framework.response import Response
from rest_framework.views import APIView
from authorization.models import ( Permission, Role, RolePermission, )
from authorization.api.serialziers import PermissionMatrixUpdateSerializer, PermissionSerializer, RoleDetailSerializer, RolePermissionUpdateSerializer, RoleSerializer
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from authorization.models import Role
from authorization.permissions.base_permissions import (
    RequiresPermission,
)
from authorization.services.role import sync_permission_matrix, sync_role_permissions

class PermissionMatrixView(APIView):

    permission_classes = [
        RequiresPermission
    ]

    required_permission = (
        "auth.manage_permissions"
    )

    def get(self, request):

        roles = (
            Role.objects
            .prefetch_related(
                "role_permissions__permission"
            )
            .order_by(
                "level",
                "name",
            )
        )

        permissions = (
            Permission.objects
            .all()
            .order_by(
                "module",
                "code",
            )
        )

        assignments = {}

        for role in roles:

            assignments[
                str(role.public_id)
            ] = [
                rp.permission.code
                for rp in role.role_permissions.all()
                if rp.enabled
            ]

        permission_groups = defaultdict(
            list
        )

        for permission in permissions:

            permission_groups[
                permission.module
            ].append(
                PermissionSerializer(
                    permission
                ).data
            )

        return Response(
            {
                "roles": RoleSerializer(
                    roles,
                    many=True,
                ).data,

                "permissions": dict(
                    permission_groups
                ),

                "assignments": assignments,
            }
        )

    def put(self, request):

        serializer = (
            PermissionMatrixUpdateSerializer(
                data=request.data
            )
        )

        serializer.is_valid(
            raise_exception=True
        )

        sync_permission_matrix(
            serializer.validated_data[
                "assignments"
            ]
        )

        return Response(
            {
                "detail":
                "Permission matrix updated."
            },
            status=status.HTTP_200_OK,
        )
    

class RolePermissionManagementView(APIView):
    """
    SITE_ADMIN-only permission matrix management.
    """

    permission_classes = [RequiresPermission]

    required_permission = (
        "auth.manage_permissions"
    )

    def get_role(self, public_id):
        return get_object_or_404(
            Role.objects.prefetch_related(
                "role_permissions__permission"
            ),
            public_id=public_id,
        )

    def get(self, request, public_id):

        role = self.get_role(public_id)

        serializer = RoleDetailSerializer(
            role,
            context={
                "request": request,
            },
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )

    def put(self, request, public_id):

        role = self.get_role(public_id)

        serializer = (
            RolePermissionUpdateSerializer(
                data=request.data
            )
        )

        serializer.is_valid(
            raise_exception=True
        )

        sync_role_permissions(
            role=role,
            permission_codes=serializer.validated_data[
                "permissions"
            ],
        )

        role.refresh_from_db()

        response_serializer = (
            RoleDetailSerializer(
                role,
                context={
                    "request": request,
                },
            )
        )

        return Response(
            response_serializer.data,
            status=status.HTTP_200_OK,
        )