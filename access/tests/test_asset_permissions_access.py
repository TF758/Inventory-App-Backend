

# from core.tests.utils._asset_permission_base import AssetPermissionTestBase


# class EquipmentPermissionAccessTests(
#     AssetPermissionTestBase
# ):

#     asset_url_name = "equipments"
#     asset_detail_url_name = "equipment-detail"

#     def _post_payload(self, room):

#         return {
#             "name": "Test Equipment",
#             "room": room.public_id,
#             "serial_number": "TEST123",
#         }

#     def test_room_viewer(self):

#         self._test_role(
#             self.room_viewer_user,
#             "ROOM_VIEWER",
#         )

#     def test_room_clerk(self):

#         self._test_role(
#             self.room_clerk_user,
#             "ROOM_CLERK",
#         )

#     def test_room_admin(self):

#         self._test_role(
#             self.room_admin_user,
#             "ROOM_ADMIN",
#         )

#     def test_location_admin(self):

#         self._test_role(
#             self.location_admin_user,
#             "LOCATION_ADMIN",
#         )

#     def test_department_admin(self):

#         self._test_role(
#             self.department_admin_user,
#             "DEPARTMENT_ADMIN",
#         )

#     def test_site_admin(self):

#         self._test_role(
#             self.site_admin_user,
#             "SITE_ADMIN",
#         )