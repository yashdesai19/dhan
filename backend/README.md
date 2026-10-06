# DHAN Backend

The core backend infrastructure powering the **DHAN Financial Platform**.

---

## 🏛️ Architecture Overview

```text
       DHAN Mobile App (React Native)
                     ↓
             FastAPI Service (Async REST API)
                     ↓
            PostgreSQL Database (Shared)
                     ↑
          Django Admin Service (Internal Management)
                     ↓
                Django Admin
```

- **FastAPI**: Serves the mobile client and external clients with asynchronous, high-throughput endpoints using SQLAlchemy 2.x and Pydantic v2.
- **PostgreSQL**: Unified persistent storage with clean separation of schema and models across application layers.
- **Django**: Powers the internal backoffice and administrative portal using Django Admin, connected to the same PostgreSQL database.

---

## 🚀 Tech Stack

- **Python 3.12+** (tested with Python 3.13)
- **FastAPI** (asynchronous mobile API)
- **Django** (internal admin panel)
- **PostgreSQL 16**
- **SQLAlchemy 2.x** (with asyncpg for async DB operations)
- **Alembic** (schema migrations)
- **Pydantic v2** (data validation and schemas)
- **Docker & Docker Compose** (orchestration)
- **pytest & pytest-asyncio** (test suite)
- **Ruff** (linting and code formatting)
- **mypy** (static type checking)

---

## 📁 Directory Structure

```text
backend/
├── fastapi_app/          # Mobile API application layer
│   ├── api/              # Versioned API routes & endpoints
│   │   └── v1/
│   │       ├── endpoints/
│   │       │   └── health.py
│   │       └── router.py
│   ├── core/             # Application config and settings
│   │   └── config.py
│   ├── db/               # Async engine, sessionmaker, base classes
│   │   ├── base.py
│   │   └── session.py
│   ├── models/           # SQLAlchemy 2.0 ORM models
│   │   └── health.py
│   ├── repositories/     # Data access layer repositories
│   │   └── base.py
│   ├── schemas/          # Pydantic v2 request/response schemas
│   │   └── health.py
│   ├── services/         # Business logic services
│   └── main.py           # FastAPI entrypoint
├── django_admin/         # Internal management layer
│   ├── apps/
│   │   └── core/         # Core administrative app & models
│   ├── config/           # Django project configuration & settings
│   │   ├── settings.py
│   │   ├── urls.py
│   │   ├── wsgi.py
│   │   └── asgi.py
│   └── manage.py         # Django CLI utility
├── alembic/              # Database migration scripts
│   ├── versions/
│   ├── env.py
│   └── script.py.mako
├── tests/                # Test suite
│   ├── conftest.py
│   ├── test_health.py
│   ├── test_db_connection.py
│   └── test_django_setup.py
├── docker-compose.yml    # Docker Compose multi-service definition
├── Dockerfile            # Container image definition
├── pyproject.toml        # Ruff, mypy, pytest configs
├── requirements.txt      # Core production dependencies
├── requirements-dev.txt  # Development & test tooling
├── alembic.ini           # Alembic migration configuration
├── .env.example          # Environment variable template
└── README.md
```

---

## ⚡ Quick Start

### 1. Prerequisites
- Python 3.12+ (or Python 3.13)
- Docker & Docker Compose

### 2. Running with Docker Compose (Recommended)
```bash
cd backend
docker compose up --build
```

Services will start:
- **FastAPI API**: http://localhost:8001
- **FastAPI Interactive Docs**: http://localhost:8001/docs
- **FastAPI Health Check**: http://localhost:8001/health
- **Django Admin Portal**: http://localhost:8002/admin/
- **PostgreSQL**: localhost:5432

### 3. Local Development Setup
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Or .venv\Scripts\activate on Windows
pip install -r requirements-dev.txt

# Run FastAPI locally
uvicorn fastapi_app.main:app --reload --port 8000

# Run Django Admin locally
python django_admin/manage.py runserver 8002
```

---

## 🧪 Testing & Code Quality

```bash
# Run test suite
pytest

# Code linting
ruff check .

# Static type checking
mypy fastapi_app
```
