# Local Development Setup (No Docker)

> Complete guide for setting up the ARMS backend locally on your machine without Docker.

This guide is for developers who want to run the application directly on their local machine using local PostgreSQL and Redis instances.

---

## Prerequisites

| Requirement | Version    | Notes                          |
| ----------- | ---------- | ------------------------------ |
| Python      | 3.12+      | Required for local development |
| PostgreSQL  | 15+        | **Must be installed locally**  |
| Redis       | 7+         | **Must be installed locally**  |
| Git         | Any recent | For cloning the repository     |

---

## Overview

Running locally means you'll need to set up:

1. **PostgreSQL** — Database for storing application data
2. **Redis** — Cache and message broker for Celery
3. **Python Environment** — Virtual environment with dependencies
4. **Django Application** — The ARMS backend itself

---

## Quick Start (Recommended)

````bash
git clone <repository-url>
cd Inventory-App-Backend

python -m venv .venv

# Activate environment
# Linux / macOS
source .venv/bin/activate

# Windows
.venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env.dev

python manage.py migrate
python manage.py setup_app
python manage.py runserver

Then open:

http://localhost:8000/api/docs/

## Step 1: Install PostgreSQL

### Windows

1. Download PostgreSQL from https://www.postgresql.org/download/windows/
2. Run the installer
3. Set a password for the `postgres` user
4. Keep default port `5432`

### macOS

```bash
# Using Homebrew
brew install postgresql@15
brew services start postgresql@15
````

### Linux (Ubuntu/Debian)

```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
```

### Create Database and User

```bash
# Connect to PostgreSQL

psql -U postgres

# Create database
CREATE DATABASE inventory;

# Create user
CREATE USER inventory WITH PASSWORD 'inventory';

# Grant privileges
GRANT ALL PRIVILEGES ON DATABASE inventory TO inventory;
GRANT ALL ON SCHEMA public TO inventory;

# Exit
\q
```

---

## Step 2: Install Redis

### Windows

Redis doesn't run natively on Windows. Options:

1. **WSL2** — Install Redis inside WSL
2. **Memurai** — https://www.memurai.com/ (Redis-compatible for Windows)
3. **WSL** — Run Redis inside WSL

```bash
# If using WSL
sudo apt install redis-server
sudo service redis-server start
```

### macOS

```bash
brew install redis
brew services start redis
```

### Linux (Ubuntu/Debian)

```bash
sudo apt install redis-server
sudo systemctl start redis-server
```

### Verify Redis

```bash
redis-cli ping
# Should return: PONG
```

---

## Step 3: Clone and Setup Project

```bash
# Clone the repository
git clone <repository-url>
cd Inventory-App-Backend
```

---

## Step 4: Create Virtual Environment

```bash
# Create virtual environment
python -m venv .venv

# Activate it
# Linux/Mac:
source .venv/bin/activate
# Windows:
.venv\Scripts\activate
```

---

## Step 5: Install Dependencies

```bash
# Install Python packages
pip install -r requirements.txt
```

---

## Step 6: Configure Environment

Copy the example environment file and update it:

```bash
cp .env.example .env.dev
```

Edit `.env.dev` with your local settings:

```env
# Django Settings
DJANGO_SECRET_KEY=your-secret-key-here-change-in-production
DJANGO_ENV=dev
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database (match your PostgreSQL setup)
DB_NAME=inventory
DB_USER=inventory
DB_PASSWORD=inventory
DB_HOST=localhost
DB_PORT=5432

# Redis (match your Redis setup)
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1

# JWT Settings
JWT_SECRET_KEY=your-jwt-secret-key-here
JWT_ACCESS_TOKEN_LIFETIME=60
JWT_REFRESH_TOKEN_LIFETIME=1440
```

---

## Step 7: Run Migrations

```bash
# Apply database migrations
python manage.py migrate
```

---

## Step 8: Create Admin User

```bash
# Create superuser account
python manage.py createsuperuser
# Follow prompts for email, password, etc.
```

---

## Step 9: Seed Initial Data (Recommended)

```bash
# Populate database with initial data
python manage.py setup_app
```

This command runs:
| Step | Command | Description |
|------|---------|-------------|
| 1 | `seed_db` | Creates departments, locations, rooms, roles, users |
| 2 | `backfill_public_id_registry` | Ensures all public IDs are registered |
| 3 | `generate_history` | Creates historical analytics data |
| 4 | `generate_asset_return_data` | Generates sample return request data |
| 5 | `generate_periodic_data` | Sets up periodic task data |
| 6 | `setup_db_cleaners` | Configures automated cleanup schedulers |

**Options:**

```bash
# Skip specific steps
python manage.py setup_app --skip-seed
python manage.py setup_app --skip-history

# Dry run (testing)
python manage.py setup_app --dry-run
```

---

## Step 10: Start Development Servers

**Django Server (API)**

```bash
python manage.py runserver
```

**Celery Worker (Background Tasks)**

```bash
celery -A inventory worker -l info
```

**Celery Beat (Scheduled Tasks)**

```bash
celery -A inventory beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

**Daphne (ASGI with WebSocket Support)**

```bash
daphne -b 0.0.0.0 -p 8000 inventory.asgi:application
```

---

## Default Credentials

After running `setup_app`, you can log in with:

| Role             | Email                 | Password          |
| ---------------- | --------------------- | ----------------- |
| Super Admin      | admin@example.com     | adminpassword     |
| Site Admin       | siteadmin@example.com | siteadminpassword |
| Department Admin | deptadmin@example.com | deptadminpassword |
| User             | user@example.com      | userpassword      |

> **Security Note**: Change these passwords in production!

---

## Running Tests

```bash
# Run all tests
python manage.py test

# Run specific app tests
python manage.py test core
python manage.py test assets

# Run with coverage
coverage run --manage.py test
coverage report
```

---

## Development Workflow

### Making Migrations

When you modify models:

```bash
# Create migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate
```

### Creating New Apps

```bash
python manage.py startapp new_app
```

### Loading Sample Data

```bash
# Generate analytics history
python manage.py generate_history

# Generate return request data
python manage.py generate_asset_return_data
```

---

## Troubleshooting

### Database Connection Issues

```bash
# Check PostgreSQL is running
# Windows: Check Services app or run:
sc query postgresql-x64-15

# macOS:
brew services list

# Linux:
sudo systemctl status postgresql

# Test connection manually
psql -h localhost -U inventory -d inventory

# Verify credentials in .env.dev
```

### Redis Connection Issues

```bash
# Check Redis is running
redis-cli ping
# Should return: PONG

# If not running:
# macOS: brew services start redis
# Linux: sudo systemctl start redis-server
# Windows: Start Memurai or WSL redis-server
```

### Migration Errors

```bash
# Check migration status
python manage.py showmigrations

# Reset database (development only!)
dropdb inventory && createdb inventory && python manage.py migrate
```

### Celery Worker Not Processing Tasks

```bash
# Check worker is running
celery -A inventory inspect active

# Check Redis connection
celery -A inventory inspect ping

# Restart worker
# Stop with Ctrl+C, then:
celery -A inventory worker -l info
```

### Port Conflicts

If ports are already in use:

```bash
# Find process using port
# Windows:
netstat -ano | findstr :8000
netstat -ano | findstr :5432
netstat -ano | findstr :6379

# Linux/Mac:
lsof -i :8000
lsof -i :5432
lsof -i :6379

# Stop the conflicting process or modify .env.dev to use different ports
```

### psycopg2 Installation Issues

If you encounter errors installing `psycopg2`:

```bash
# Windows: Install Visual C++ Build Tools, then:
pip install psycopg2-binary

# Or use:
pip install psycopg2
```

---

## Project Structure

```
Inventory-App-Backend/
├── .env.dev              # Environment variables (your local config)
├── manage.py             # Django management script
├── requirements.txt      # Python dependencies
│
├── core/                 # Shared infrastructure
├── assets/               # Asset management
├── assignments/          # Assignment workflows
├── users/                # User management
├── sites/                # Site hierarchy
├── reporting/            # Report generation
├── analytics/            # Metrics & snapshots
├── data_import/          # CSV bulk imports
│
├── inventory/            # Django project settings
└── docs/                 # Documentation
```

---

## Next Steps

- Review [API Documentation](http://localhost:8000/api/docs/)
- Explore [Core Models](core/core.md)
- Learn about [Asset Management](assets/assets.md)
- Understand [Authentication](../users/users.md)

---

## Related Documentation

- [README.md](../README.md) — Project overview
- [Core Documentation](core/core.md) — Shared infrastructure
- [Assets Documentation](assets/assets.md) — Asset models
- [Users Documentation](users/users.md) — User & role management
- [Core Tests](core_tests.md) — Test coverage analysis
