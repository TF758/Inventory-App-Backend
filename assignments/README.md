# Assignments — Asset Assignment & Accountability

> Django app handling the assignment of assets to users, tracking who has what, and managing return workflows.

The `assignments` app provides the domain logic for asset accountability, ensuring every asset can be traced to a responsible person.

---

## Overview

The assignments app manages the lifecycle of asset custody — from initial assignment to return. It tracks equipment, accessories, and consumables issued to users, with full audit trails and validation rules.

This follows the **domain-driven design** pattern — all assignment-related concerns are encapsulated here.

---

## What Assignments Provides

### Assignment Types

| Type       | Model                 | Description                                          |
| ---------- | --------------------- | ---------------------------------------------------- |
| Equipment  | `EquipmentAssignment` | One-to-one assignment of equipment to a user         |
| Accessory  | `AccessoryAssignment` | Many-to-one assignment of accessories with quantity  |
| Consumable | `ConsumableIssue`     | Consumable issuance with remaining quantity tracking |

### EquipmentAssignment

One-to-one relationship between equipment and user:

```python
class EquipmentAssignment(models.Model):
    equipment = models.OneToOneField(Equipment, on_delete=models.CASCADE, related_name="active_assignment")
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name="equipment_assignments")

    assigned_at = models.DateTimeField(auto_now_add=True)
    returned_at = models.DateTimeField(null=True, blank=True)

    assigned_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="equipment_assigned")

    notes = models.TextField(blank=True)
```

Features:

- One-to-one with Equipment (prevents double assignment)
- Tracks who assigned and when
- Notes field for assignment context
- Return tracking via `returned_at`

### AccessoryAssignment

Many-to-one relationship for accessories with quantity:

```python
class AccessoryAssignment(models.Model):
    accessory = models.ForeignKey(Accessory, on_delete=models.CASCADE, related_name="assignments")
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name="accessory_assignments")

    quantity = models.PositiveIntegerField()
    assigned_at = models.DateTimeField(auto_now_add=True)
    returned_at = models.DateTimeField(null=True, blank=True)

    assigned_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
```

Features:

- Multiple accessories can be assigned to one user
- Quantity tracking for bulk items
- Return tracking

### ConsumableIssue

Complex consumable tracking with remaining quantity:

```python
class ConsumableIssue(models.Model):
    consumable = models.ForeignKey(Consumable, on_delete=models.CASCADE, related_name="issues")
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name="consumable_assignments")
    quantity = models.PositiveIntegerField()  # Remaining quantity
    issued_quantity = models.PositiveIntegerField()  # Original quantity issued
    assigned_at = models.DateTimeField(auto_now_add=True)
    returned_at = models.DateTimeField(null=True, blank=True)
    assigned_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="assigned_consumables")
    purpose = models.CharField(max_length=255, blank=True)
```

Features:

- Tracks both issued and remaining quantity
- Unique constraint: only ONE open issue per (consumable, user)
- Validation constraints:
  - `quantity >= 0` — never negative
  - `issued_quantity > 0` — must be positive
  - `quantity <= issued_quantity` — can't exceed original
  - If `returned_at` set, `quantity` must be zero
- `is_active` property: `returned_at is None and quantity > 0`

### EquipmentEvent

Audit trail for equipment lifecycle events:

```python
class EquipmentEvent(models.Model):
    class Event_Choices(models.TextChoices):
        ASSIGNED = "assigned", "Assigned"
        RETURNED = "returned", "Returned"
        LOST = "lost", "Lost"
        DAMAGED = "damaged", "Damaged"
        REPAIRED = "repaired", "Repaired"
        RETIRED = "retired", "Retired"
        UNDER_REPAIR = "under_repair", "Under repair"
        CONDEMNED = "condemned", "Condemned"
        RETURN_REQUESTED = "return_requested", "Return Requested"

    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE, related_name="events")
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    event_type = models.CharField(max_length=20, choices=Event_Choices)
    occurred_at = models.DateTimeField(auto_now_add=True)
    reported_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="reported_equipment_events")
    notes = models.TextField(blank=True)
```

---

## Architecture

```
assignments/
├── models/
│   └── asset_assignment.py  # EquipmentAssignment, AccessoryAssignment, ConsumableIssue, EquipmentEvent
├── api/
│   ├── serializers/         # DRF serializers
│   └── viewsets/            # API view sets
├── selectors/               # QuerySet builders
├── services/                # Business logic
├── tasks/                   # Celery tasks
├── filters/                 # Filter backends
├── factories/               # Test factories
├── tests/                   # Unit tests
├── urls/                    # URL routing
└── utils/                   # Helper functions
```

---

## Key Patterns

### Active Assignment Detection

Equipment uses a reverse relation to check assignment status:

```python
# In Equipment model
@property
def is_assigned(self) -> bool:
    try:
        return self.active_assignment.returned_at is None
    except EquipmentAssignment.DoesNotExist:
        return False
```

### Consumable Active Check

```python
@property
def is_active(self):
    return self.returned_at is None and self.quantity > 0
```

### Unique Open Issue Constraint

Only one active issue per user/consumable:

```python
models.UniqueConstraint(
    fields=["consumable", "user"],
    condition=Q(returned_at__isnull=True),
    name="unique_open_issue_per_user_consumable",
)
```

---

## Usage

### Assigning Equipment

```python
from assignments.models import EquipmentAssignment

assignment = EquipmentAssignment.objects.create(
    equipment=equipment,
    user=user,
    assigned_by=admin_user,
    notes="Assigned for development work"
)
```

### Issuing Consumables

```python
from assignments.models import ConsumableIssue

issue = ConsumableIssue.objects.create(
    consumable=consumable,
    user=user,
    quantity=10,
    issued_quantity=10,
    assigned_by=admin_user,
    purpose="Q2 project supplies"
)
```

### Recording Equipment Events

```python
from assignments.models import EquipmentEvent

event = EquipmentEvent.objects.create(
    equipment=equipment,
    user=user,
    event_type=EquipmentEvent.Event_Choices.ASSIGNED,
    reported_by=admin_user,
    notes="Assigned for remote work"
)
```

### Querying User Assignments

```python
# Get all active equipment assignments for a user
user.equipment_assignments.filter(returned_at__isnull=True)

# Get all active consumable issues for a user
user.consumable_assignments.filter(returned_at__isnull=True, quantity__gt=0)
```

---

## Dependencies

- **assets** — Equipment, Accessory, Consumable models
- **users** — User model
- **sites** — Room model (via equipment)
- **core** — PublicIDModel, base classes

---

## API Endpoints

Typical endpoints:

- `POST /api/assignments/equipment/` — Assign equipment to user
- `POST /api/assignments/equipment/{id}/return/` — Return equipment
- `POST /api/assignments/accessories/` — Assign accessories
- `POST /api/assignments/consumables/` — Issue consumables
- `GET /api/assignments/events/` — List equipment events

---

## Testing

Run assignment-specific tests:

```bash
python manage.py test assignments
```

---

## Related Documentation

- [Assets](../assets/README.md)
- [Users](../users/README.md)
- [Core Models](../core/README.md)
- [API Overview](../README.md)
