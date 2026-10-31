# RESQ Backend Phase 1 - Setup Instructions

## Current Status: Database Models Complete ✓

All SQLAlchemy 2.0 models have been created following `docs/database/database-schema.md`:
- ✓ Organization, User models with relationships
- ✓ Incident, IncidentReport, TrackingToken models
- ✓ ResponseTask with self-referential parent_task_id
- ✓ HospitalCapacity with CHECK constraints
- ✓ AmbulanceStatus, ResourceInventory, ResourceReservation
- ✓ StatusEvent, AgentEvent, AuditLog (append-only logs)
- ✓ All PostGIS Geography fields with GIST indexes
- ✓ Database configuration with async (asyncpg) and sync (psycopg2) engines
- ✓ Alembic initialized and configured
- ✓ Enhanced health check endpoint with database connectivity test

## Next Steps to Complete Phase 1:

### Step 1: Start PostgreSQL Database

**Option A - Using PowerShell (Recommended):**
```powershell
# From the RESQ_MAIN directory, run:
.\start-database.ps1
```

**Option B - Using Docker Desktop:**
1. Open Docker Desktop application
2. Ensure Docker engine is running
3. Open PowerShell in RESQ_MAIN directory and run:
```powershell
docker compose up -d
```

**Option C - Manual Docker Commands:**
```powershell
docker compose up -d postgres
docker compose up -d redis
```

### Step 2: Generate Initial Database Migration

Once PostgreSQL is running, create the initial migration:

```bash
# From RESQ_MAIN directory
cd backend
..\venv\Scripts\alembic.exe revision --autogenerate -m "Initial schema with all Phase 1 tables"
```

This will create a migration file in `backend/migrations/versions/` containing all 13 tables.

### Step 3: Apply the Migration

```bash
# Still in backend/ directory
..\venv\Scripts\alembic.exe upgrade head
```

This executes the migration and creates all tables in PostgreSQL.

### Step 4: Verify Database Setup

Start the FastAPI server:
```bash
# From backend/ directory
..\venv\Scripts\uvicorn.exe app.main:app --reload --host 0.0.0.0 --port 8000
```

Then test the health endpoint:
```bash
# In another terminal
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "service": "resq-backend",
  "version": "0.1.0",
  "timestamp": "2026-10-31T08:30:00.000Z",
  "database": "connected"
}
```

### Step 5: Run Automated Tests

```bash
# From RESQ_MAIN directory
.\venv\Scripts\pytest backend/tests/ -v
```

All tests should pass, verifying database connectivity and model integrity.

## Troubleshooting

### Issue: Docker not found
- Ensure Docker Desktop is installed and running
- Run commands in PowerShell (not Git Bash)

### Issue: Port 5432 already in use
```powershell
# Stop any existing PostgreSQL services
docker compose down
# Or find and stop the conflicting process
netstat -ano | findstr :5432
```

### Issue: Alembic can't connect to database
- Verify `.env` file has correct `DATABASE_SYNC_URL`
- Check PostgreSQL is running: `docker compose ps`
- Test connection manually using psql or pgAdmin

### Issue: PostGIS extension error
The migration will automatically create the PostGIS extension. If it fails:
```sql
-- Connect to database and run manually:
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
```

## File Structure Created

```
backend/
├── app/
│   ├── database/
│   │   ├── __init__.py
│   │   ├── base.py (Base, BaseModel with UUIDv4 + timestamps)
│   │   └── config.py (async/sync engines, get_db dependency)
│   ├── models/
│   │   ├── __init__.py (exports all models)
│   │   ├── organization.py
│   │   ├── user.py
│   │   ├── incident.py
│   │   ├── incident_report.py
│   │   ├── tracking_token.py
│   │   ├── response_task.py
│   │   ├── hospital_capacity.py
│   │   ├── ambulance_status.py
│   │   ├── resource_inventory.py
│   │   ├── resource_reservation.py
│   │   ├── status_event.py
│   │   ├── agent_event.py
│   │   └── audit_log.py
│   └── main.py (Enhanced with database lifespan and health check)
├── migrations/
│   ├── versions/ (migration files will be here)
│   ├── env.py (configured with all models + GeoAlchemy2)
│   ├── script.py.mako
│   └── README
├── alembic.ini (configured to use DATABASE_SYNC_URL)
└── tests/
    └── test_health.py

```

## Phase 1 Completion Checklist

- [x] Configure Python backend project environment
- [x] Set up FastAPI core application
- [x] Configure PostgreSQL 16 + PostGIS connection engine
- [x] Set up SQLAlchemy ORM models matching schema spec
- [x] Configure Alembic migrations
- [ ] **Generate initial database migration script** ← YOU ARE HERE
- [ ] **Apply migration and verify tables created**
- [ ] Implement FastAPI health check endpoint (DONE, needs DB test)
- [ ] Run automated backend health tests
- [ ] Update `docs/team/progress/backend-progress.md`

## Commands Summary

```powershell
# 1. Start database
.\start-database.ps1

# 2. Generate migration (from backend/)
cd backend
..\venv\Scripts\alembic.exe revision --autogenerate -m "Initial schema with all Phase 1 tables"

# 3. Apply migration
..\venv\Scripts\alembic.exe upgrade head

# 4. Start server
..\venv\Scripts\uvicorn.exe app.main:app --reload

# 5. Test (in new terminal, from RESQ_MAIN/)
curl http://localhost:8000/health
.\venv\Scripts\pytest backend/tests/ -v
```
