# authorization/tests/utils.py

from authorization.models import (
    Permission,
    Role,
    RolePermission,
)

from users.models import User
from users.models.roles import RoleAssignment

from sites.models import Department


class PermissionTestFixture:

    @classmethod
    def build(cls):

        department = Department.objects.create(
            name="Test Department"
        )

        view_permission = Permission.objects.create(
            code="test.view",
            name="Test View",
            module="test",
        )

        edit_permission = Permission.objects.create(
            code="test.edit",
            name="Test Edit",
            module="test",
        )

        delete_permission = Permission.objects.create(
            code="test.delete",
            name="Test Delete",
            module="test",
        )

        viewer_role = Role.objects.create(
            code="VIEWER_TEST",
            name="Viewer Test",
            scope_type="DEPARTMENT",
            level=10,
        )

        admin_role = Role.objects.create(
            code="ADMIN_TEST",
            name="Admin Test",
            scope_type="DEPARTMENT",
            level=60,
        )

        RolePermission.objects.bulk_create([
            RolePermission(
                role=viewer_role,
                permission=view_permission,
            ),
            RolePermission(
                role=admin_role,
                permission=view_permission,
            ),
            RolePermission(
                role=admin_role,
                permission=edit_permission,
            ),
            RolePermission(
                role=admin_role,
                permission=delete_permission,
            ),
        ])

        viewer = User.objects.create(
            email="viewer@test.com",
        )

        admin = User.objects.create(
            email="admin@test.com",
        )

        site_admin = User.objects.create(
            email="siteadmin@test.com",
            is_staff=True,
            is_superuser=True,
        )

        viewer_assignment = RoleAssignment.objects.create(
            user=viewer,
            role="DEPARTMENT_VIEWER",
            role_ref=viewer_role,
            department=department,
        )

        admin_assignment = RoleAssignment.objects.create(
            user=admin,
            role="DEPARTMENT_ADMIN",
            role_ref=admin_role,
            department=department,
        )

        site_admin_assignment = RoleAssignment.objects.create(
            user=site_admin,
            role="SITE_ADMIN",
        )

        viewer.active_role = viewer_assignment
        admin.active_role = admin_assignment
        site_admin.active_role = site_admin_assignment

        User.objects.bulk_update(
            [viewer, admin, site_admin],
            ["active_role"],
        )

        return {
            "department": department,
            "viewer": viewer,
            "admin": admin,
            "site_admin": site_admin,
            "viewer_role": viewer_role,
            "admin_role": admin_role,
        }