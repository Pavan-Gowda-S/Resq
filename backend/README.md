# RESQ Backend & Database Service

## 1. Overview
The RESQ backend is a FastAPI application built with PostgreSQL 16 + PostGIS, SQLAlchemy ORM, Alembic migrations, and Redis. It is owned and maintained by **Developer 1 (Backend & Database)**.

---

## 2. Setup & Execution

### Prerequisites
- Python 3.10+
- Docker & Docker Compose (for PostgreSQL/PostGIS and Redis)

### Quick Start
1. Start infrastructure containers:
   ```bash
   docker compose up -d db redis
   ```
2. Create and activate a Python virtual environment:
   ```bash
   python -m venv venv
   # Windows:
   .\venv\Scripts\Activate.ps1
   # Linux/macOS:
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r backend/requirements.txt
   ```
4. Copy environment configuration:
   ```bash
   cp .env.example .env
   ```
5. Run the development server:
   ```bash
   uvicorn backend.app.main:app --reload --port 8000
   ```
6. Run the test suite:
   ```bash
   pytest backend/tests
   ```

---

## 3. Directory Layout
- `app/api/`: REST API routes and endpoints.
- `app/models/`: SQLAlchemy ORM database models.
- `app/schemas/`: Pydantic request/response schemas.
- `app/services/`: Deterministic business logic (capacity calculations, reservations, offline sync).
- `app/database/`: Engine, session maker, and base declarative classes.
- `app/auth/`: JWT authentication, password hashing, and RBAC guards.
- `app/realtime/`: WebSocket managers and Redis Pub/Sub workers.
- `migrations/`: Alembic schema migration versions.
- `tests/`: Automated unit and integration tests.
