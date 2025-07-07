from rest_framework.permissions import BasePermission

class IsCreateRole(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'creator'

class IsUpdateDeleteRole(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in ['editor', 'admin']
    


class IsOwnDepartmentPermission(BasePermission):
    """
    Allows actions only on the user's own department.
    """

    def has_object_permission(self, request, view, obj):
        """
        Check if the user has permission to access the object."""
        
        if request.user.is_authenticated and request.user.department:
            return obj.id == request.user.department.id
        return False

    def has_permission(self, request, view):
        # For create actions, check if user is authenticated
        return request.user.is_authenticated