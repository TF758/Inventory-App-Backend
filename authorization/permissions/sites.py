from authorization.permissions.base_permissions import ScopedPermission




class DepartmentPermission(ScopedPermission):
    """
    Authorization for Department endpoints.

    Business rules such as:
        - department rename restrictions
        - department creation restrictions

    belong in services/viewsets.
    """

    permission_map = {
        "GET": "departments.view",
        "POST": "departments.create",
        "PUT": "departments.update",
        "PATCH": "departments.update",
        "DELETE": "departments.delete",
    }

class LocationPermission(ScopedPermission):
    """
    Authorization for Location endpoints.

    Business rules such as:
        - moving locations between departments

    belong in services/viewsets.
    """

    permission_map = {
        "GET": "locations.view",
        "POST": "locations.create",
        "PUT": "locations.update",
        "PATCH": "locations.update",
        "DELETE": "locations.delete",
    }


class RoomPermission(ScopedPermission):
    """
    Authorization for Room endpoints.

    Business rules such as:
        - moving rooms between locations

    belong in services/viewsets.
    """

    permission_map = {
        "GET": "rooms.view",
        "POST": "rooms.create",
        "PUT": "rooms.update",
        "PATCH": "rooms.update",
        "DELETE": "rooms.delete",
    }