from django.test import SimpleTestCase

from access.role_permission_boundaries import (
    is_permission_allowed_for_role,
    is_viewer_safe_permission,
)


class RolePermissionBoundaryPolicyTests(SimpleTestCase):
    """
    Unit tests for role-permission compatibility boundaries.

    The boundary policy only answers:

        "Can this role type ever be granted this permission code?"

    These tests intentionally avoid the database. They do not test:
        - whether a role currently has the permission
        - object scope
        - role governance
        - serializers
        - DRF permissions
    """

    # ------------------------------------------------------------------
    # Empty / invalid input
    # ------------------------------------------------------------------

    def test_empty_role_or_permission_is_not_allowed(self):
        self.assertFalse(
            is_permission_allowed_for_role(
                "",
                "assets.view",
            )
        )
        self.assertFalse(
            is_permission_allowed_for_role(
                "ROOM_ADMIN",
                "",
            )
        )
        self.assertFalse(
            is_permission_allowed_for_role(
                "",
                "",
            )
        )

    def test_empty_permission_is_not_viewer_safe(self):
        self.assertFalse(
            is_viewer_safe_permission("")
        )

    # ------------------------------------------------------------------
    # SITE_ADMIN system authority
    # ------------------------------------------------------------------

    def test_site_admin_is_allowed_any_permission_if_policy_is_called(self):
        """
        SITE_ADMIN should normally be excluded from the editable matrix
        upstream. If this compatibility policy is called directly, it
        treats SITE_ADMIN as system authority.
        """

        for permission_code in [
            "assets.hard_delete",
            "auth.manage_permissions",
            "departments.delete",
            "unknown.permission",
        ]:
            with self.subTest(permission_code=permission_code):
                self.assertTrue(
                    is_permission_allowed_for_role(
                        "SITE_ADMIN",
                        permission_code,
                    )
                )

    # ------------------------------------------------------------------
    # Viewer-safe permissions
    # ------------------------------------------------------------------

    def test_common_viewer_safe_permissions_are_allowed_for_all_viewer_roles(self):
        viewer_roles = [
            "ROOM_VIEWER",
            "LOCATION_VIEWER",
            "DEPARTMENT_VIEWER",
        ]

        safe_permissions = [
            "assets.view",
            "rooms.view",
            "role_assignments.self_view",
            "reports.inventory_summary",
            "reports.site_audit_logs",
            "returns.self_return",
            "returns.request_asset_return",
            "role_assignments.self_activate",
            "sessions.self_view",
            "sessions.self_revoke",
            "users.self_update",
        ]

        for role in viewer_roles:
            for permission_code in safe_permissions:
                with self.subTest(role=role, permission_code=permission_code):
                    self.assertTrue(
                        is_permission_allowed_for_role(
                            role,
                            permission_code,
                        )
                    )


    def test_viewer_roles_only_receive_view_permissions_within_their_hierarchy_level(self):
        allowed_by_role = {
            "ROOM_VIEWER": [
                "rooms.view",
            ],
            "LOCATION_VIEWER": [
                "locations.view",
                "rooms.view",
            ],
            "DEPARTMENT_VIEWER": [
                "departments.view",
                "locations.view",
                "rooms.view",
            ],
        }

        for role, permission_codes in allowed_by_role.items():
            for permission_code in permission_codes:
                with self.subTest(role=role, permission_code=permission_code):
                    self.assertTrue(
                        is_permission_allowed_for_role(
                            role,
                            permission_code,
                        )
                    )

    def test_viewer_write_admin_and_governance_permissions_are_blocked(self):
        viewer_roles = [
            "ROOM_VIEWER",
            "LOCATION_VIEWER",
            "DEPARTMENT_VIEWER",
        ]
        blocked_permissions = [
            "assets.create",
            "assets.update",
            "assets.delete",
            "assets.hard_delete",
            "assignments.create",
            "assignments.update",
            "assignments.unassign",
            "assignments.reassign",
            "returns.process",
            "role_assignments.create",
            "role_assignments.update",
            "role_assignments.delete",
            "role_assignments.manage",
            "user_placements.create",
            "user_placements.update",
            "user_placements.delete",
            "users.lock",
            "users.unlock",
            "locations.transfer",
            "rooms.transfer",
        ]

        for role in viewer_roles:
            for permission_code in blocked_permissions:
                with self.subTest(role=role, permission_code=permission_code):
                    self.assertFalse(
                        is_permission_allowed_for_role(
                            role,
                            permission_code,
                        )
                    )

    # ------------------------------------------------------------------
    # ROOM_CLERK operational boundary
    # ------------------------------------------------------------------

    def test_room_clerk_can_receive_basic_operational_permissions(self):
        allowed_permissions = [
            "assets.view",
            "assets.create",
            "assets.update",
            "assets.use",
            "assignments.create",
            "returns.create",
            "agreements.attach_items",
            "agreements.detach_items",
            "consumables.report_loss",
            "reports.asset_history",
        ]

        for permission_code in allowed_permissions:
            with self.subTest(permission_code=permission_code):
                self.assertTrue(
                    is_permission_allowed_for_role(
                        "ROOM_CLERK",
                        permission_code,
                    )
                )

    def test_room_clerk_cannot_receive_structure_governance_or_security_permissions(self):
        blocked_permissions = [
            "departments.view",
            "departments.create",
            "locations.view",
            "locations.update",
            "rooms.update",
            "rooms.delete",
            "role_assignments.create",
            "role_assignments.self_activate",
            "user_placements.view",
            "sessions.view",
            "sessions.self_view",
            "users.full_create",
            "users.update",
            "users.lock",
            "assets.delete",
            "returns.process",
        ]

        for permission_code in blocked_permissions:
            with self.subTest(permission_code=permission_code):
                self.assertFalse(
                    is_permission_allowed_for_role(
                        "ROOM_CLERK",
                        permission_code,
                    )
                )

    # ------------------------------------------------------------------
    # Room-level admin boundary
    # ------------------------------------------------------------------

    def test_room_admin_can_receive_room_level_operational_and_governance_permissions(self):
        allowed_permissions = [
            "assets.create",
            "assets.update",
            "assets.delete",
            "assignments.create",
            "assignments.update",
            "assignments.unassign",
            "assignments.reassign",
            "returns.process",
            "role_assignments.create",
            "role_assignments.update",
            "role_assignments.delete",
            "user_placements.create",
            "user_placements.update",
            "rooms.view",
            "rooms.update",
        ]

        for permission_code in allowed_permissions:
            with self.subTest(permission_code=permission_code):
                self.assertTrue(
                    is_permission_allowed_for_role(
                        "ROOM_ADMIN",
                        permission_code,
                    )
                )

    def test_room_roles_cannot_receive_location_or_department_permissions(self):
        room_roles = [
            "ROOM_VIEWER",
            "ROOM_CLERK",
            "ROOM_ADMIN",
        ]
        blocked_permissions = [
            "departments.view",
            "departments.create",
            "departments.update",
            "departments.delete",
            "locations.view",
            "locations.create",
            "locations.update",
            "locations.transfer",
            "locations.delete",
        ]

        for role in room_roles:
            for permission_code in blocked_permissions:
                with self.subTest(role=role, permission_code=permission_code):
                    self.assertFalse(
                        is_permission_allowed_for_role(
                            role,
                            permission_code,
                        )
                    )

    def test_room_admin_cannot_receive_room_create_delete_or_transfer_permissions(self):
        blocked_permissions = [
            "rooms.create",
            "rooms.transfer",
            "rooms.delete",
        ]

        for permission_code in blocked_permissions:
            with self.subTest(permission_code=permission_code):
                self.assertFalse(
                    is_permission_allowed_for_role(
                        "ROOM_ADMIN",
                        permission_code,
                    )
                )

    # ------------------------------------------------------------------
    # Location-level boundary
    # ------------------------------------------------------------------

    def test_location_admin_can_receive_location_and_room_operational_permissions(self):
        allowed_permissions = [
            "locations.view",
            "locations.update",
            "rooms.view",
            "rooms.create",
            "rooms.update",
            "rooms.transfer",
            "rooms.delete",
            "assets.create",
            "assets.update",
            "assets.delete",
            "assignments.create",
            "returns.process",
            "role_assignments.create",
            "user_placements.update",
        ]

        for permission_code in allowed_permissions:
            with self.subTest(permission_code=permission_code):
                self.assertTrue(
                    is_permission_allowed_for_role(
                        "LOCATION_ADMIN",
                        permission_code,
                    )
                )

    def test_location_roles_cannot_receive_department_permissions(self):
        location_roles = [
            "LOCATION_VIEWER",
            "LOCATION_ADMIN",
        ]
        blocked_permissions = [
            "departments.view",
            "departments.create",
            "departments.update",
            "departments.delete",
        ]

        for role in location_roles:
            for permission_code in blocked_permissions:
                with self.subTest(role=role, permission_code=permission_code):
                    self.assertFalse(
                        is_permission_allowed_for_role(
                            role,
                            permission_code,
                        )
                    )

    def test_location_admin_cannot_receive_location_create_delete_or_transfer_permissions(self):
        blocked_permissions = [
            "locations.create",
            "locations.transfer",
            "locations.delete",
        ]

        for permission_code in blocked_permissions:
            with self.subTest(permission_code=permission_code):
                self.assertFalse(
                    is_permission_allowed_for_role(
                        "LOCATION_ADMIN",
                        permission_code,
                    )
                )

    # ------------------------------------------------------------------
    # Department-level boundary
    # ------------------------------------------------------------------

    def test_department_admin_can_receive_department_location_room_and_admin_permissions(self):
        allowed_permissions = [
            "departments.view",
            "departments.create",
            "departments.update",
            "locations.view",
            "locations.create",
            "locations.update",
            "locations.transfer",
            "locations.delete",
            "rooms.view",
            "rooms.create",
            "rooms.update",
            "rooms.transfer",
            "rooms.delete",
            "agreements.create",
            "agreements.update",
            "agreements.delete",
            "users.full_create",
            "users.update",
            "users.delete",
            "users.lock",
            "users.unlock",
            "role_assignments.create",
            "role_assignments.update",
            "role_assignments.delete",
            "user_placements.create",
            "user_placements.update",
        ]

        for permission_code in allowed_permissions:
            with self.subTest(permission_code=permission_code):
                self.assertTrue(
                    is_permission_allowed_for_role(
                        "DEPARTMENT_ADMIN",
                        permission_code,
                    )
                )

    def test_department_viewer_remains_viewer_even_at_department_scope(self):
        self.assertTrue(
            is_permission_allowed_for_role(
                "DEPARTMENT_VIEWER",
                "departments.view",
            )
        )
        self.assertFalse(
            is_permission_allowed_for_role(
                "DEPARTMENT_VIEWER",
                "departments.update",
            )
        )
        self.assertFalse(
            is_permission_allowed_for_role(
                "DEPARTMENT_VIEWER",
                "locations.create",
            )
        )
        self.assertFalse(
            is_permission_allowed_for_role(
                "DEPARTMENT_VIEWER",
                "users.lock",
            )
        )

    # ------------------------------------------------------------------
    # Site-admin-only permissions
    # ------------------------------------------------------------------

    def test_site_admin_only_permissions_are_blocked_for_non_site_roles(self):
        non_site_roles = [
            "ROOM_VIEWER",
            "ROOM_CLERK",
            "ROOM_ADMIN",
            "LOCATION_VIEWER",
            "LOCATION_ADMIN",
            "DEPARTMENT_VIEWER",
            "DEPARTMENT_ADMIN",
        ]
        site_admin_only_permissions = [
            "auth.manage_permissions",
            "roles.manage_permissions",
            "permissions.view",
            "assets.hard_delete",
            "assignments.view_all",
            "reports.manage",
            "sessions.view",
            "sessions.revoke",
            "role_assignments.activate",
            "users.create",
        ]

        for role in non_site_roles:
            for permission_code in site_admin_only_permissions:
                with self.subTest(role=role, permission_code=permission_code):
                    self.assertFalse(
                        is_permission_allowed_for_role(
                            role,
                            permission_code,
                        )
                    )
