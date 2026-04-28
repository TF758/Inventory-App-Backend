# ARMS — Enterprise Asset & Inventory Management Backend

> Scalable backend platform for managing assets, inventory, assignments, audits, and reporting across multi-site organizations.

Built for organizations that need stronger operational control than spreadsheets or fragmented tools can provide.

![Python](https://img.shields.io/badge/Python-3.x-blue)
![Django](https://img.shields.io/badge/Django-5.x-green)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-blue)
![Redis](https://img.shields.io/badge/Redis-7+-red)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## Overview

ARMS is a production-ready backend system designed for organizations that manage equipment, consumables, accessories, and operational assets across multiple departments, locations, and rooms.

It centralizes asset ownership, assignment workflows, stock visibility, reporting, and compliance processes into one secure API platform.

The system is especially suited for environments where assets move frequently, accountability matters, and leadership requires automated operational reporting.

### Ideal Use Cases

- Schools / Universities
- Government agencies
- Healthcare institutions
- Multi-branch private companies
- Warehouses / Logistics operations
- NGOs / Enterprise operations teams

---

## Why ARMS Exists

Many organizations still manage inventory using spreadsheets, email chains, or disconnected legacy systems.

This creates problems such as:

- Missing or untracked equipment
- Poor ownership accountability
- No audit trail for asset movement
- Slow manual reporting processes
- Inconsistent stock visibility across sites
- Difficult return / reassignment workflows
- Weak operational oversight

ARMS solves this through structured workflows, centralized data, secure access controls, and automated reporting.

---

## Core Features

### Asset Operations

- Full lifecycle tracking for equipment, accessories, consumables, and components
- Unique public asset IDs
- Status management (active, damaged, under repair, retired, lost, condemned)
- Batch operations for large inventory actions

### Multi-Site Management

- Department → Location → Room hierarchy
- Track assets across distributed facilities
- User room placement tracking
- Site-level reporting and visibility

### Assignment & Accountability

- Assign assets to users
- Reassign / return workflows
- Return request approvals
- Assignment history and ownership records

### Governance & Security

- Role-based access control
- JWT authentication
- Session revocation / expiry management
- Immutable audit logs of critical actions

### Automation & Productivity

- CSV bulk imports
- Asynchronous report generation
- Notifications and alerts
- Low-stock monitoring
- Scheduled metrics jobs

---

## Engineering Highlights

- Modular monolith architecture using Django apps by business domain
- Asynchronous task processing with Celery + Redis
- PostgreSQL-backed relational data model
- Role-based permissions system with active role switching
- Soft delete + historical audit retention patterns
- Scalable reporting pipelines for heavy exports
- Redis-backed caching, queues, and real-time channels
- Production-ready Dockerized deployment stack

---

## Backend Architecture

```text
Client Applications
(Web Frontend / Admin / Integrations)
            ↓
        Django REST API
            ↓
       PostgreSQL Database

Redis ─── Cache / Broker / Channels
Celery ── Reports / Imports / Scheduled Jobs
Nginx ─── Reverse Proxy / TLS
```

---

## Tech Stack

| Layer             | Technology                |
| ----------------- | ------------------------- |
| Backend Framework | Django 5.x                |
| API               | Django REST Framework     |
| Database          | PostgreSQL                |
| Queue / Cache     | Redis                     |
| Background Jobs   | Celery                    |
| Realtime          | Django Channels           |
| Deployment        | Docker + Nginx            |
| API Documentation | OpenAPI / Swagger / ReDoc |

## Quick Start

```bash
git clone <repository-url>
cd arms-backend
cp .env.example .env
docker-compose up -d
```

Run migrations:

```bash
docker-compose exec api python manage.py migrate
```

Create admin user:

```bash
docker-compose exec api python manage.py createsuperuser
```

### Full Application Setup

The `setup_app` command runs a complete initialization pipeline:

```bash
docker-compose exec api python manage.py setup_app
```

**What it does:**

| Step | Command                       | Description                                                 |
| ---- | ----------------------------- | ----------------------------------------------------------- |
| 1    | `seed_db`                     | Creates initial departments, locations, rooms, roles, users |
| 2    | `backfill_public_id_registry` | Ensures all public IDs are registered                       |
| 3    | `generate_history`            | Creates historical analytics data                           |
| 4    | `generate_asset_return_data`  | Generates sample return request data                        |
| 5    | `generate_periodic_data`      | Sets up periodic task data                                  |
| 6    | `setup_db_cleaners`           | Configures automated cleanup schedulers                     |

**Options:**

```bash
# Skip specific steps
docker-compose exec api python manage.py setup_app --skip-seed
docker-compose exec api python manage.py setup_app --skip-history
docker-compose exec api python manage.py setup_app --skip-backfill --skip-periodic

# Dry run (for testing)
docker-compose exec api python manage.py setup_app --dry-run
```

> **Note**: After running `setup_app`, you can log in with the seeded admin credentials or create a new superuser.

## API Modules

- Authentication
- Users & Roles
- Assets
- Assignments
- Returns
- Reporting
- Analytics
- Notifications
- Imports

## API Documentation

Interactive OpenAPI documentation is included for development, testing, and frontend integration.

- Swagger UI: `/docs/`
- ReDoc Reference Docs: `/redoc/`
- OpenAPI Schema: `/schema/`

Supports authenticated endpoint testing via JWT Bearer tokens directly in Swagger UI.

## Environment Configuration

The project auto-loads environment files based on runtime context:

- `.env.dev` → Docker development environment
- `.env.local` → Local machine execution
- `.env.example` → Starter template for new setups

When running via Docker, the application defaults to `.env.dev`.
