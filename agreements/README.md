# Agreements — Contract, Coverage & Lifecycle Management

> Django app for managing asset agreements, coverage boundaries, attached assets, and lifecycle events.

The `agreements` app models legal and service agreements that can cover inventory assets at the department, location, room, or global level.

---

## Overview

The agreements app provides the domain layer for tracking contracts, warranties, service agreements, and other coverage relationships that apply to assets in the inventory system.

It follows the **domain-driven design** pattern — all agreement-related responsibilities are encapsulated here.

The app separates three concepts:

- **Agreement definitions** (`AssetAgreement`) — the legal or commercial contract itself
- **Coverage rules** (`AgreementCoverage`) — where and how the agreement applies
- **Agreement membership** (`AssetAgreementItem`) — actual assets enrolled under the agreement

It also stores lifecycle history and supports operations such as expiry, renewal, extension, and termination.

---

## What Agreements Provides

### AssetAgreement

The primary agreement model:

- Agreement name and vendor
- Agreement type, status, start/expiry/renewal dates
- Auto-renew, cost, currency, notes
- Managing department ownership

This model uses `PUBLIC_ID_PREFIX = "AGR"`.

### AgreementCoverage

Defines eligibility boundaries for an agreement.

Coverage may be scoped as:

- Global
- Department
- Location
- Room

Coverage does not automatically enroll assets; it only controls whether an asset can be attached.

Key coverage rules:

- Global coverage cannot coexist with scoped coverage
- Department coverage supersedes location/room scope
- Location coverage supersedes room scope
- Duplicate exact scopes are rejected

### AssetAgreementItem

Represents an actual asset enrolled under an agreement.

Assets may be one of:

- `equipment`
- `consumable`
- `accessory`

Key behaviors:

- Exactly one asset type per item
- Quantity validation (`equipment` items require quantity 1)
- Coverage date validation
- Asset snapshots for name, serial, and public ID at attach time
- Eligibility validation against agreement coverage

This model uses `PUBLIC_ID_PREFIX = "AGI"`.

### History Models

Tracks lifecycle and membership events:

- `AgreementHistory` — agreement status changes, renewals, expirations, terminations
- `AgreementItemHistory` — attachment/removal snapshots for agreement assets

---

## Architecture

```
agreements/
├── api/
│   ├── serialziers/    # DRF serializers for agreement models
│   └── viewsets/       # API view sets for agreements and lifecycle actions
├── models/
│   └── agreements.py   # AssetAgreement, AgreementCoverage, AssetAgreementItem, history models
├── services/          # Lifecycle services and business logic
├── tasks/             # Scheduled Celery task(s)
├── tests/             # Unit tests
├── urls/              # URL routing
└── agreement_factories.py # Test factory helpers
```

---

## Key Patterns

### Coverage Scope and Eligibility

Coverage rules are separate from asset membership. The app enforces:

- global coverage as the broadest scope
- scoped coverage only for department/location/room assets
- no redundant or overlapping coverage entries

### Asset Enrollment vs. Eligibility

An asset can be eligible for an agreement without being attached to it.

Only `AssetAgreementItem` creates an active membership between an asset and an agreement.

### Asset Snapshotting

Agreement items snapshot asset metadata at attach time:

```python
self.asset_name_snapshot = asset.name or ""
self.asset_public_id_snapshot = asset.public_id or ""
self.asset_serial_snapshot = getattr(asset, "serial_number", "") or ""
```

This preserves history even if the asset changes later.

### Lifecycle Service

`AgreementLifecycleService` centralizes agreement lifecycle transitions:

- expire agreements when expiry date passes
- terminate agreements explicitly
- extend expiry dates
- renew agreements

A scheduled Celery task syncs expired agreements automatically.

---

## API Surface

### Agreement endpoints

- `GET /agreements/` — list agreements
- `POST /agreements/` — create agreement
- `GET /agreements/active/` — active agreements
- `GET /agreements/expired/` — expired agreements
- `GET /agreements/expiring/` — expiring agreements
- `GET /agreements/applicable/` — applicable agreements for scope or asset
- `GET /agreements/by-asset/` — agreements by asset
- `GET /agreements/<public_id>/` — retrieve agreement
- `PUT/PATCH /agreements/<public_id>/` — update agreement
- `DELETE /agreements/<public_id>/` — delete agreement
- `GET /agreements/<public_id>/coverages/` — list coverage entries
- `GET /agreements/<public_id>/items/` — list enrolled assets
- `GET /agreements/<public_id>/history/` — agreement history

### Lifecycle endpoints

- `POST /agreements/<public_id>/terminate/`
- `POST /agreements/<public_id>/extend/`
- `POST /agreements/<public_id>/renew/`

### Coverage endpoints

- `GET /agreements/coverages/`
- `POST /agreements/coverages/`
- `GET /agreements/coverages/<public_id>/`
- `PUT/PATCH /agreements/coverages/<public_id>/`
- `DELETE /agreements/coverages/<public_id>/`

### Agreement item endpoints

- `GET /agreements/items/`
- `POST /agreements/items/attach/`
- `GET /agreements/items/<public_id>/`
- `POST /agreements/items/<public_id>/detach/`

### History endpoints

- `GET /agreements/history/`
- `GET /agreements/history/<pk>/`
- `GET /agreements/item-history/`
- `GET /agreements/item-history/<pk>/`

---

## Usage

### Creating an agreement

```python
from agreements.models.agreements import AssetAgreement, AgreementType

agreement = AssetAgreement.objects.create(
    name="Dell Warranty",
    agreement_type=AgreementType.WARRANTY,
    vendor="Dell",
    start_date="2025-01-01",
    expiry_date="2026-01-01",
    managing_department=department,
)
```

### Defining coverage

```python
from agreements.models.agreements import AgreementCoverage, CoverageScopeType

AgreementCoverage.objects.create(
    agreement=agreement,
    scope_type=CoverageScopeType.LOCATION,
    location=location,
)
```

### Attaching an asset

```python
from agreements.models.agreements import AssetAgreementItem

AssetAgreementItem.objects.create(
    agreement=agreement,
    equipment=equipment,
    quantity=1,
    coverage_start="2025-01-01",
    coverage_end="2026-01-01",
)
```

### Expiring agreements

A scheduled task keeps agreement state current:

```python
from agreements.tasks.agreement_lifecycle import sync_expired_agreements
sync_expired_agreements.delay()
```

---

## Dependencies

- **assets** — Equipment, Accessory, Consumable models
- **sites** — Department, Location, Room models
- **core** — PublicIDModel, task scheduling, base services
- **users** — User model for history events

---

## Testing

Run agreements-specific tests:

```bash
python manage.py test agreements
```

---

## Notes

- `AgreementCoverage` defines eligibility rules; it does not auto-enroll assets.
- `AssetAgreementItem` requires exactly one asset type per item.
- Agreement item snapshots preserve asset metadata even after updates.
- Lifecycle events are recorded for audit and reporting.
