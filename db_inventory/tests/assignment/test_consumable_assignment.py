from django.utils import timezone
from django.test import TestCase
from rest_framework.test import APIClient
from django.urls import reverse
from db_inventory.factories import (
    DepartmentFactory,
    LocationFactory,
    RoomFactory,
    UserFactory,
    UserLocationFactory,
    ConsumableFactory,
)
from db_inventory.models.asset_assignment import ConsumableIssue
from db_inventory.models.roles import RoleAssignment

class ConsumableAPITestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.issue_url = reverse("issue-consumable")
        self.use_url = reverse("use-consumable")
        self.return_url = reverse("return-consumable")
        self.report_loss_url = reverse("report-consumable-loss")




class TestIssueConsumable(ConsumableAPITestCase):

    def test_room_admin_can_issue_consumable(self):
        dept = DepartmentFactory()
        loc = LocationFactory(department=dept)
        room = RoomFactory(location=loc)

        admin = UserFactory()
        RoleAssignment.objects.create(user=admin,role="ROOM_ADMIN",room=room,)
        admin.active_role = admin.role_assignments.first()
        admin.save()

        user = UserFactory()
        UserLocationFactory(user=user, room=room)

        consumable = ConsumableFactory(room=room, quantity=20)

        self.client.force_authenticate(admin)

        response = self.client.post(
            self.issue_url,
            {
                "consumable": consumable.public_id,
                "user": user.public_id,
                "quantity": 5,
                "purpose": "Daily ops",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        consumable.refresh_from_db()
        self.assertEqual(consumable.quantity, 15)

        issue = ConsumableIssue.objects.get( consumable=consumable, user=user, returned_at__isnull=True, )
        self.assertEqual(issue.quantity, 5)
        self.assertEqual(issue.issued_quantity, 5)


    def test_user_cannot_use_more_than_issued(self):
            user = UserFactory()
            consumable = ConsumableFactory()

            issue = ConsumableIssue.objects.create( consumable=consumable, user=user, quantity=3, issued_quantity=3, )

            self.client.force_authenticate(user)

            response = self.client.post(
                self.use_url,
                {
                    "consumable": consumable.public_id,
                    "quantity": 5,
                },
                format="json",
            )

            self.assertEqual(response.status_code, 400)

            issue.refresh_from_db()
            self.assertEqual(issue.quantity, 3)

class TestReportConsumableLoss(ConsumableAPITestCase):

    def test_user_can_report_loss_on_own_issue(self):
        user = UserFactory()
        consumable = ConsumableFactory(quantity=50)

        issue = ConsumableIssue.objects.create( consumable=consumable, user=user, quantity=10, issued_quantity=10, )

        self.client.force_authenticate(user)

        response = self.client.post(
            self.report_loss_url,
            {
                "consumable": consumable.public_id,
                "quantity": 3,
                "event_type": "lost",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        issue.refresh_from_db()
        self.assertEqual(issue.quantity, 7)

        consumable.refresh_from_db()
        self.assertEqual(consumable.quantity, 50)

    def test_user_cannot_report_loss_for_other_user(self):
            user_a = UserFactory()
            user_b = UserFactory()
            consumable = ConsumableFactory()

            ConsumableIssue.objects.create( consumable=consumable, user=user_a, quantity=5, issued_quantity=5, )

            self.client.force_authenticate(user_b)

            response = self.client.post(
                self.report_loss_url,
                {
                    "consumable": consumable.public_id,
                    "quantity": 1,
                    "event_type": "lost",
                },
                format="json",
            )

            self.assertEqual(response.status_code, 404)

class TestReturnConsumable(ConsumableAPITestCase):

    def test_admin_can_return_unused_consumable(self):
        dept = DepartmentFactory()
        loc = LocationFactory(department=dept)
        room = RoomFactory(location=loc)

        admin = UserFactory()
        RoleAssignment.objects.create( user=admin, role="ROOM_ADMIN", room=room, )
        admin.active_role = admin.role_assignments.first()
        admin.save()

        user = UserFactory()
        UserLocationFactory(user=user, room=room)

        consumable = ConsumableFactory(room=room, quantity=10)

        issue = ConsumableIssue.objects.create( consumable=consumable, user=user, quantity=6, issued_quantity=6, )

        self.client.force_authenticate(admin)

        response = self.client.post(
            self.return_url,
            {
                "issue": issue.id,
                "quantity": 4,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        issue.refresh_from_db()
        self.assertEqual(issue.quantity, 2)

        consumable.refresh_from_db()
        self.assertEqual(consumable.quantity, 14)

    def test_user_cannot_return_consumable(self):
        user = UserFactory()
        consumable = ConsumableFactory()

        issue = ConsumableIssue.objects.create( consumable=consumable, user=user, quantity=3, issued_quantity=3, )

        self.client.force_authenticate(user)

        response = self.client.post(
            self.return_url,
            {
                "issue": issue.id,
                "quantity": 1,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 403)

class TestConsumableEdgeCases(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.issue_url = reverse("issue-consumable")
        self.use_url = reverse("use-consumable")
        self.return_url = reverse("return-consumable")
        self.report_loss_url = reverse("report-consumable-loss")

    def test_user_cannot_use_closed_consumable_issue(self):
        user = UserFactory()
        consumable = ConsumableFactory(quantity=10)

        issue = ConsumableIssue.objects.create( consumable=consumable, user=user, quantity=0, issued_quantity=5, returned_at=timezone.now(), )
        self.client.force_authenticate(user)

        response = self.client.post(
            self.use_url,
            {
                "consumable": consumable.public_id,
                "quantity": 1,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 404)

    def test_user_cannot_report_loss_on_closed_issue(self):
        user = UserFactory()
        consumable = ConsumableFactory()

        issue = ConsumableIssue.objects.create( consumable=consumable, user=user, quantity=0, issued_quantity=5, returned_at=timezone.now(), )

        self.client.force_authenticate(user)

        response = self.client.post(
            self.report_loss_url,
            {
                "consumable": consumable.public_id,
                "quantity": 1,
                "event_type": "lost",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 404)

    def test_admin_cannot_return_zero_quantity(self):
        dept = DepartmentFactory()
        loc = LocationFactory(department=dept)
        room = RoomFactory(location=loc)

        admin = UserFactory()
        RoleAssignment.objects.create( user=admin, role="ROOM_ADMIN", room=room, )
        admin.active_role = admin.role_assignments.first()
        admin.save()

        user = UserFactory()
        UserLocationFactory(user=user, room=room)

        consumable = ConsumableFactory(room=room, quantity=10)

        issue = ConsumableIssue.objects.create(
            consumable=consumable,
            user=user,
            quantity=5,
            issued_quantity=5,
        )

        self.client.force_authenticate(admin)

        response = self.client.post(
            self.return_url,
            {
                "issue": issue.id,
                "quantity": 0,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)

    def test_action_denied_when_active_role_scope_does_not_match(self):
        dept = DepartmentFactory()
        loc = LocationFactory(department=dept)

        room_a = RoomFactory(location=loc)
        room_b = RoomFactory(location=loc)

        admin = UserFactory()

        # Has admin role for room A…
        RoleAssignment.objects.create(
            user=admin,
            role="ROOM_ADMIN",
            room=room_a,
        )
        # …but active role is unrelated room B
        RoleAssignment.objects.create( user=admin, role="ROOM_VIEWER", room=room_b, )

        admin.active_role = admin.role_assignments.last()
        admin.save()

        user = UserFactory()
        UserLocationFactory(user=user, room=room_a)

        consumable = ConsumableFactory(room=room_a, quantity=10)

        self.client.force_authenticate(admin)

        response = self.client.post(
            self.issue_url,
            {
                "consumable": consumable.public_id,
                "user": user.public_id,
                "quantity": 1,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 403)

    def test_anonymous_user_cannot_access_consumable_endpoints(self):
        consumable = ConsumableFactory()

        response = self.client.post(
            self.use_url,
            {
                "consumable": consumable.public_id,
                "quantity": 1,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 401)