# Sites — Organization Hierarchy & Location Management

> Django app handling the organizational hierarchy: departments, locations, rooms, and user placements.

The `sites` app provides the spatial structure for ARMS, enabling multi-site organizations to track assets and users across physical locations.

---

## Overview

The sites app defines the physical organization hierarchy — from departments down to individual rooms. It also tracks where users are physically located, enabling room-based access control and asset assignment.

This follows the **domain-driven design** pattern — all location-related concerns are encapsulated here.

---

## What Sites Provides

### Location Hierarchy

| Level      | Model        | Prefix | Description                       |
| ---------- | ------------ | ------ | --------------------------------- |
| Department | `Department` | `DPT`  | Top-level organizational unit     |
| Location   | `Location`   | `LOC`  | Physical site within a department |
| Room       | `Room`       | `RM`   | Specific room within a location   |

### Department

Top-level organizational unit:

```python
class Department(PublicIDModel):
    PUBLIC_ID_PREFIX = "DPT"

    name = models.CharField(max_length=255, unique=True)
    description = models.CharField(blank=True, max_length=500)
    img_link = models.URLField(blank=True, default='')
```

Features:

- Unique name constraint
- Optional description and image
- Contains multiple locations

### Location

Physical site within a department:

```python
class Location(PublicIDModel):
    PUBLIC_ID_PREFIX = "LOC"

    name = models.CharField(max_length=255)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, related_name="locations")
```

Features:

- Unique name per department constraint
- Links to parent department
- Contains multiple rooms

### Room

Specific room within a location:

```python
class Room(PublicIDModel):
    PUBLIC_ID_PREFIX = "RM"

    location = models.ForeignKey(Location, on_delete=models.SET_NULL, null=True, related_name="rooms")
    name = models.CharField(max_length=255)
```

Features:

- Unique name per location constraint
- Links to parent location (and thus department)
- Assets and users can be assigned to rooms

### UserPlacement

Tracks user room assignment history:

```python
class UserPlacement(PublicIDModel):
    """
    Tracks the physical room assignment history of a user.
    Only one location may be marked as current per user.
    """

    PUBLIC_ID_PREFIX = "UP"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="user_placements")
    room = models.ForeignKey(Room, on_delete=models.SET_NULL, null=True, blank=True, related_name="user_placements")

    is_current = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)
```

Features:

- Tracks user location history
- Only one current placement per user
- Useful for room-based access control

---

## Architecture

```
sites/
├── models/
│   └── sites.py   # Department, Location, Room, UserPlacement
├── api/
│   ├── serializers/    # DRF serializers
│   └── viewsets/       # API view sets
├── selectors/          # QuerySet builders
├── services/           # Business logic
├── permissions/        # Site-based permission classes
├── tasks/              # Celery tasks
├── filters/            # Filter backends
├── factories/          # Test factories
├── tests/              # Unit tests
├── urls/               # URL routing
└── utils/              # Helper functions
```

---

## Key Patterns

### Hierarchy Traversal

Rooms can access their full hierarchy:

```python
room.location  # Location
room.location.department  # Department

# Or via audit_label
room.audit_label()  # "Conference Room (Location: Building A, Department: IT)"
```

### Unique Constraints

Locations and rooms have unique constraints:

```python
# Location: unique name per department
models.UniqueConstraint(
    fields=["department", "name"],
    name="unique_location_name_per_department"
)

# Room: unique name per location
models.UniqueConstraint(
    fields=["location", "name"],
    name="unique_room_name_per_location"
)
```

### Current User Placement

```python
# Get user's current room
current_placement = user.user_placements.filter(is_current=True).first()
current_room = current_placement.room if current_placement else None
```

---

## Usage

### Creating a Department

```python
from sites.models import Department

dept = Department.objects.create(
    name="Information Technology",
    description="IT Department",
    img_link="https://example.com/it-dept.jpg"
)
# Generates public_id: DPT-XXXXX
```

### Creating a Location

```python
from sites.models import Location

location = Location.objects.create(
    name="Main Office",
    department=dept
)
# Generates public_id: LOC-XXXXX
```

### Creating a Room

```python
from sites.models import Room

room = Room.objects.create(
    name="Conference Room A",
    location=location
)
# Generates public_id: RM-XXXXX
```

### Placing a User

```python
from sites.models import UserPlacement

# First, unset any current placement
user.user_placements.update(is_current=False)

# Create new placement
placement = UserPlacement.objects.create(
    user=user,
    room=room,
    is_current=True
)
# Generates public_id: UP-XXXXX
```

### Querying Locations

```python
# Get all locations in a department
dept.locations.all()

# Get all rooms in a location
location.rooms.all()

# Get all users in a room
room.user_placements.filter(is_current=True)
```

---

## Integration with Other Apps

### Assets

Equipment, accessories, and consumables are assigned to rooms:

```python
equipment = Equipment.objects.create(
    name="Projector",
    room=room
)
```

### Assignments

Asset assignments track who has what:

```python
assignment = EquipmentAssignment.objects.create(
    equipment=equipment,
    user=user
)
```

### Users & Roles

Role assignments can be scoped to rooms, locations, or departments:

```python
role = RoleAssignment.objects.create(
    user=user,
    role="ROOM_ADMIN",
    room=room
)
```

---

## Dependencies

- **core** — PublicIDModel, base classes
- **users** — User model for UserPlacement

---

## API Endpoints

Typical endpoints:

- `GET /api/sites/departments/` — List departments
- `POST /api/sites/departments/` — Create department
- `GET /api/sites/locations/` — List locations
- `POST /api/sites/locations/` — Create location
- `GET /api/sites/rooms/` — List rooms
- `POST /api/sites/rooms/` — Create room
- `GET /api/sites/placements/` — List user placements
- `POST /api/sites/placements/` — Assign user to room

---

## Testing

Run site-specific tests:

```bash
python manage.py test sites
```

---

## Related Documentation

- [Users](../users/README.md)
- [Assets](../assets/README.md)
- [Assignments](../assignments/README.md)
- [Core Models](../core/README.md)
- [API Overview](../README.md)
