from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from db_inventory.models import AuditLog, RoleAssignment, User
from db_inventory.factories import (
    UserFactory, AdminUserFactory,
    DepartmentFactory, LocationFactory, RoomFactory,
    EquipmentFactory
)

class AuditLogTests(TestCase):
    def setUp(self):
        # API client
        self.client = APIClient()

        # Departments, Locations, Rooms
        self.department = DepartmentFactory(name="IT")
        self.department.save()

        self.location = LocationFactory( name= "Test Location", department=self.department)
        self.location.save()

        self.room = RoomFactory(name="Test Room", location=self.location)
        self.room.save()

        # Users
        self.site_admin = AdminUserFactory()
        self.site_admin_role = RoleAssignment.objects.create(
            user=self.site_admin,
            role="SITE_ADMIN",
            department=None,
            location=None,
            room=None,
            assigned_by=self.site_admin
        )
        self.site_admin.active_role = self.site_admin_role
        self.site_admin.save()

       
        self.dept_admin = User.objects.create_user(
            email="deptadmin@example.com",
            password="StrongP@ssw0rd!",
            fname="Dept",
            lname="Admin",
            job_title="Manager",
            is_active=True
        )
        self.dept_admin_role = RoleAssignment.objects.create(
            user=self.dept_admin,
            role="DEPARTMENT_ADMIN",
            department=self.department,
            location=None,
            room=None,
            assigned_by=self.dept_admin
        )
        self.dept_admin.active_role = self.dept_admin_role
        self.dept_admin.save()

        # Equipment
        self.equipment = EquipmentFactory(name ="Tets Equipment", room=self.room)

    def test_audit_log_created_on_equipment_create(self):
        self.client.force_authenticate(user=self.site_admin)
        url = reverse("equipments") 
        response = self.client.post(url, {"name": "New Equip", "room": self.room.public_id})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        audit = AuditLog.objects.last()
        self.assertEqual(audit.event_type, AuditLog.Events.MODEL_CREATED)
        self.assertEqual(audit.target_model, "Equipment")
        self.assertIsNotNone(audit.target_id)
        self.assertEqual(audit.room, self.room)
        self.assertEqual(audit.location, self.room.location)
        self.assertEqual(audit.department, self.room.location.department)
        self.assertEqual(audit.user, self.site_admin)

    def test_audit_log_created_on_equipment_update(self):
        self.client.force_authenticate(user=self.site_admin)
        url = reverse("equipment-detail", args=[self.equipment.public_id])
        response = self.client.patch(url, {"name": "Updated Name"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        audit = AuditLog.objects.last()
        self.assertEqual(audit.event_type, AuditLog.Events.MODEL_UPDATED)
        self.assertEqual(audit.target_model, "Equipment")
        self.assertEqual(audit.target_id, self.equipment.public_id)
        self.assertEqual(audit.user, self.site_admin)

    def test_audit_log_created_on_equipment_delete(self):
        self.client.force_authenticate(user=self.site_admin)
        url = reverse("equipment-detail", args=[self.equipment.public_id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        audit = AuditLog.objects.last()
        self.assertEqual(audit.event_type, AuditLog.Events.MODEL_DELETED)
        self.assertEqual(audit.target_model, "Equipment")
        self.assertEqual(audit.target_id, self.equipment.public_id)
        self.assertEqual(audit.user, self.site_admin)

    def test_scope_filter_dept_admin(self):
        self.client.force_authenticate(user=self.dept_admin)
        url = reverse("equipments")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Department admin should only see equipment in their department
        for item in response.data['results']:
            equipment_room_department = EquipmentFactory._meta.model.objects.get(
                public_id=item['public_id']
            ).room.location.department
            self.assertEqual(equipment_room_department, self.dept_admin.active_role.department)

    def test_audit_log_user_email_and_public_id(self):
        self.client.force_authenticate(user=self.site_admin)
        url = reverse("equipments")
        response = self.client.post(url, {"name": "Email Test Equip", "room": self.room.public_id})
        audit = AuditLog.objects.last()
        self.assertEqual(audit.user_email, self.site_admin.email)
        self.assertEqual(audit.user_public_id, self.site_admin.public_id)

    def test_viewer_cannot_create_equipment(self):
        viewer = UserFactory()
        viewer_role = RoleAssignment.objects.create(user=viewer, role="ROOM_VIEWER", room=self.room, assigned_by=self.site_admin)
        viewer.active_role = viewer_role
        viewer.save()
        
        self.client.force_authenticate(user=viewer)
        url = reverse("equipments")
        response = self.client.post(url, {"name": "Blocked Equip", "room": self.room.public_id})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_audit_log_persists_after_equipment_deleted_from_db(self):
        """
        Ensure audit logs retain target_id and metadata even after the related object is deleted.
        """
        self.client.force_authenticate(user=self.site_admin)

        # First check equipment exists
        equip_public_id = self.equipment.public_id
        equip_room = self.equipment.room
        equip_location = equip_room.location
        equip_department = equip_location.department

        url = reverse("equipment-detail", args=[equip_public_id])
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # The equipment should be fully removed from DB
        from db_inventory.models import Equipment
        self.assertFalse(Equipment.objects.filter(public_id=equip_public_id).exists())

        # The audit log entry should still exist
        audit = AuditLog.objects.last()
        self.assertIsNotNone(audit)

        # Audit log values must persist even after the record is gone
        self.assertEqual(audit.event_type, AuditLog.Events.MODEL_DELETED)
        self.assertEqual(audit.target_model, "Equipment")

        # target_id must be preserved even though Equipment is deleted
        self.assertEqual(audit.target_id, equip_public_id)

        # Room / location / department must NOT be null
        self.assertEqual(audit.room, equip_room)
        self.assertEqual(audit.location, equip_location)
        self.assertEqual(audit.department, equip_department)

        # User attribution must still be correct
        self.assertEqual(audit.user, self.site_admin)