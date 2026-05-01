# Assets — Equipment, Consumables & Inventory Management

> Django app handling the core inventory entities: equipment, accessories, consumables, and components.

The `assets` app is the central domain module for tracking physical assets throughout their lifecycle.

---

## Overview

The assets app provides the data models and business logic for managing all types of inventory items within ARMS. It supports equipment tracking with serial numbers, consumables with stock levels, accessories, and components.

This follows the **domain-driven design** pattern — all asset-related concerns are encapsulated here.

---

## What Assets Provides

### Asset Types

The app supports four asset types, each with a specific public ID prefix:

| Type       | Prefix | Description                                                              |
| ---------- | ------ | ------------------------------------------------------------------------ |
| Equipment  | `EQ`   | High-value items with serial numbers (computers, machinery, vehicles)    |
| Accessory  | `AC`   | Supporting items paired with equipment (keyboards, cables, monitors)     |
| Consumable | `CON`  | Items that deplete over time with stock tracking (paper, ink, batteries) |

### Equipment

Primary tracked assets with full lifecycle support:

```python
class Equipment(PublicIDModel):
    PUBLIC_ID_PREFIX = "EQ"

    name = models.CharField(max_length=100)
    brand = models.CharField(max_length=100, blank=True)
    model = models.CharField(max_length=100, blank=True)
    serial_number = models.CharField(max_length=50, unique=True, blank=True, null=True)
    status = models.CharField(max_length=20, choices=EquipmentStatus.choices, default=EquipmentStatus.OK)
    room = models.ForeignKey(Room, on_delete=models.SET_NULL, null=True, blank=True)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
```

Features:

- Unique serial number with validation (letters, numbers, dashes only)
- Status tracking via `EquipmentStatus` enum
- Room-based location
- Soft delete with audit trail
- Assignment tracking via `current_holder` property

### Accessory

Supporting items that accompany equipment:

```python
class Accessory(PublicIDModel):
    PUBLIC_ID_PREFIX = "AC"

    name = models.CharField(max_length=100)
    serial_number = models.CharField(max_length=100, unique=True, blank=True, null=True)
    quantity = models.PositiveIntegerField(default=0)
    room = models.ForeignKey(Room, on_delete=models.SET_NULL, null=True, blank=True)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
```

Features:

- Optional serial number tracking
- Quantity support for bulk accessories
- Room-based location
- Soft delete

### Consumable

Stock-managed items that deplete over time:

```python
class Consumable(PublicIDModel):
    PUBLIC_ID_PREFIX = "CON"

    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, max_length=255)
    quantity = models.PositiveIntegerField(default=0)
    low_stock_threshold = models.PositiveIntegerField(default=0)
    room = models.ForeignKey(Room, on_delete=models.SET_NULL, null=True, blank=True)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
```

Features:

- Quantity tracking with non-negative constraint
- Low stock threshold alerts via `is_low_stock` property
- Room-based storage
- Soft delete

### Key Features

- Unique public ID generation (EQ, AC, CON prefixes)
- Status tracking for equipment (OK, damaged, under repair, lost, retired, condemned)
- Room-based location tracking
- Serial number validation for equipment and accessories
- Quantity tracking for accessories and consumables
- Low stock threshold alerts for consumables
- Soft delete with audit trail
- Assignment tracking via `current_holder` property

### Data Models

- `Equipment` — Primary equipment with serial tracking
- `Accessory` — Equipment accessories and peripherals
- `Consumable` — Stock-managed consumable items
- `Component` — Replaceable/repairable components
- `EquipmentStatus` — Status choices enum

---

## Architecture

```
assets/
├── models/
│   └── assets.py       # Equipment, Accessory, Consumable, Component
├── api/
│   ├── serializers/    # DRF serializers
│   └── viewsets/       # API view sets
├── selectors/          # QuerySet builders
├── services/           # Business logic
├── tasks/              # Celery tasks
├── filters/            # Filter backends
├── factories/          # Test factories
├── tests/              # Unit tests
├── urls/               # URL routing
└── utils/              # Helper functions
```

---

## Key Patterns

### Public ID System

Each asset type has a prefix:

```python
class Equipment(PublicIDModel):
    PUBLIC_ID_PREFIX = "EQ"  # Generates EQ-XXXXX

class Accessory(PublicIDModel):
    PUBLIC_ID_PREFIX = "AC"  # Generates AC-XXXXX

class Consumable(PublicIDModel):
    PUBLIC_ID_PREFIX = "CS"  # Generates CS-XXXXX

class Component(PublicIDModel):
    PUBLIC_ID_PREFIX = "COM" # Generates COM-XXXXX
```

### Status Tracking

All equipment uses the `EquipmentStatus` enum:

```python
class EquipmentStatus(models.TextChoices):
    OK = "ok", "OK"
    DAMAGED = "damaged", "Damaged"
    UNDER_REPAIR = "under_repair", "Under repair"
    LOST = "lost", "Lost"
    RETIRED = "retired", "Retired"
    CONDEMNED = "condemned", "Condemned"
```

### Low Stock Detection

Consumables support low stock alerts:

```python
@property
def is_low_stock(self) -> bool:
    return (self.low_stock_threshold > 0 and self.quantity <= self.low_stock_threshold)
```

### Assignment Detection

The `is_assigned` property checks active equipment assignments:

```python
@property
def is_assigned(self) -> bool:
    try:
        return self.active_assignment.returned_at is None
    except EquipmentAssignment.DoesNotExist:
        return False
```

### Current Holder

Track who currently holds an asset:

```python
@property
def current_holder(self):
    assignment = getattr(self, "active_assignment", None)
    if assignment and assignment.returned_at is None:
        return assignment.user
    return None
```

---

## Usage

### Creating Equipment

```python
from assets.models import Equipment, EquipmentStatus

equipment = Equipment.objects.create(
    name="Dell Laptop",
    brand="Dell",
    model="XPS 15",
    serial_number="SN123456",
    status=EquipmentStatus.OK,
    room=room
)
# Generates public_id: EQ-XXXXX
```

### Creating Accessories

```python
from assets.models import Accessory

accessory = Accessory.objects.create(
    name="USB-C Hub",
    serial_number="USB123456",
    quantity=10,
    room=room
)
# Generates public_id: AC-XXXXX
```

### Creating Consumables

```python
from assets.models import Consumable

consumable = Consumable.objects.create(
    name="A4 Paper Ream",
    description="White A4 printer paper, 500 sheets",
    quantity=50,
    low_stock_threshold=10,
    room=room
)
# Generates public_id: CON-XXXXX

# Check low stock
if consumable.is_low_stock:
    print("Reorder needed!")
```

### Querying Assets

```python
from assets.selectors import equipment_list

# Get all active equipment
active = equipment_list().filter(is_deleted=False)

# Filter by status
damaged = equipment_list().filter(status=EquipmentStatus.DAMAGED)
```

---

## Dependencies

- **core** — PublicIDModel, base classes
- **sites** — Department, Location, Room models
- **assignments** — EquipmentAssignment for holder tracking

---

## API Endpoints

Typical endpoints (via `api/viewsets/`):

- `GET /api/assets/equipment/` — List equipment
- `POST /api/assets/equipment/` — Create equipment
- `GET /api/assets/equipment/{public_id}/` — Retrieve equipment
- `PATCH /api/assets/equipment/{public_id}/` — Update equipment
- `DELETE /api/assets/equipment/{public_id}/` — Soft delete equipment

Similar endpoints for accessories, consumables, and components.

---

## Testing

Run asset-specific tests:

```bash
python manage.py test assets
```

---

## Related Documentation

- [Core Models](../core/README.md)
- [Assignments](../assignments/README.md)
- [Sites](../sites/README.md)
- [API Overview](../README.md)
