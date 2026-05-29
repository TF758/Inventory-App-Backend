from rest_framework.test import APITestCase

from users.factories.user_factories import (
AdminUserFactory,
)

from users.factories.user_factories import (
RoleAssignmentFactory,
)

class AuthenticatedAPITestCase( APITestCase ):

    def setUp(self):

        super().setUp()

        self.user = (
            AdminUserFactory()
        )

        self.role_assignment = (
            RoleAssignmentFactory(
                user=self.user,
                site_admin=True,
            )
        )

        self.user.active_role = (
            self.role_assignment
        )

        self.user.save(
            update_fields=[
                "active_role"
            ]
        )

        self.client.force_authenticate(
            user=self.user
        )

