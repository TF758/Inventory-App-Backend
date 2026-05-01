from django.db.models import Q

class Scope:
    """
    Normalized representation of a user's effective scope.

    Priority:
        room > location > department
    """

    def __init__(self, role):
        self.role = role

        if role and role.room:
            self.level = "room"
            self.obj = role.room
        elif role and role.location:
            self.level = "location"
            self.obj = role.location
        elif role and role.department:
            self.level = "department"
            self.obj = role.department
        else:
            self.level = None
            self.obj = None

    def is_site_admin(self):
        return self.role and self.role.role == "SITE_ADMIN"


class BaseScopePolicy:
    """
    Base class for all queryset scoping policies.

    Subclasses must implement `apply()`.
    """

    def __init__(self, user, queryset):
        self.user = user
        self.queryset = queryset

        self.role = getattr(user, "active_role", None)

        self.scope = Scope(self.role)

    def apply(self):
        return self.queryset.none()

    # ---- shared helpers ----

    def room_hierarchy_q(self):
        if self.scope.level == "room":
            return Q(room=self.scope.obj)
        if self.scope.level == "location":
            return Q(room__location=self.scope.obj)
        if self.scope.level == "department":
            return Q(room__location__department=self.scope.obj)
        return Q()

    def location_hierarchy_q(self):
        if self.scope.level == "location":
            return Q(location=self.scope.obj)
        if self.scope.level == "department":
            return Q(location__department=self.scope.obj)
        return Q()

