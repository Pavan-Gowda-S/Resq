# RESQ — Database Schema Specification

## 1. Overview & Data Architecture

The RESQ persistence layer is built on **PostgreSQL 16** with the **PostGIS** extension for geospatial coordinates, boundaries, and spatial distance queries.

### Key Data Integrity Invariants
1. **Foreign Key Integrity:** Strict relational integrity across organizations, incidents, and tasks.
2. **Deterministic Capacity:** Capacities are constrained by column checks (e.g., `occupied + reserved + out_of_service <= total`).
3. **Auditable Immutability:** Event logs (`status_events`, `agent_events`, `audit_logs`) are append-only.
4. **Spatial Indexing:** All latitude/longitude points are indexed using PostGIS GIST indexes for ultra-fast spatial search ($<10\text{ms}$).

---

## 2. Entity Definitions

### 2.1 `organizations`
Represents registered legal/operational entities participating in the emergency network.
- `id`: UUID (Primary Key, default: `gen_random_uuid()`)
- `name`: VARCHAR(255) (NOT NULL)
- `type`: VARCHAR(50) (NOT NULL) — Enum: `RESCUE`, `HOSPITAL`, `AMBULANCE_PROVIDER`, `PHARMACY`, `BLOOD_BANK`, `SUPPLIER`, `CONTROL_ROOM`, `ADMIN`
- `registration_number`: VARCHAR(100) (UNIQUE, NULLABLE)
- `verification_status`: VARCHAR(30) (NOT NULL, default: `PENDING`) — Enum: `PENDING`, `VERIFIED`, `SUSPENDED`
- `contact_email`: VARCHAR(255) (NOT NULL)
- `contact_phone`: VARCHAR(50) (NOT NULL)
- `location`: GEOGRAPHY(POINT, 4326) (NOT NULL)
- `address`: TEXT (NOT NULL)
- `district`: VARCHAR(100) (NOT NULL) — e.g., 'Ernakulam', 'Wayanad'
- `created_at`: TIMESTAMPTZ (NOT NULL, default: `NOW()`)
- `updated_at`: TIMESTAMPTZ (NOT NULL, default: `NOW()`)

*Indexes:*
- `idx_org_type`: `(type)`
- `idx_org_location`: GIST `(location)`
- `idx_org_verification`: `(verification_status)`

---

### 2.2 `users`
Authorized operators, dispatchers, doctors, and responders affiliated with organizations.
- `id`: UUID (Primary Key)
- `organization_id`: UUID (Foreign Key $\rightarrow$ `organizations.id` ON DELETE CASCADE, NULLABLE for Superadmins)
- `email`: VARCHAR(255) (UNIQUE, NOT NULL)
- `password_hash`: VARCHAR(255) (NOT NULL)
- `full_name`: VARCHAR(255) (NOT NULL)
- `phone`: VARCHAR(50) (NOT NULL)
- `role`: VARCHAR(50) (NOT NULL) — Enum: `SUPERADMIN`, `CONTROL_ROOM_DISPATCHER`, `ORG_ADMIN`, `FIELD_RESPONDER`, `TRIAGE_DOCTOR`
- `is_active`: BOOLEAN (NOT NULL, default: `TRUE`)
- `created_at`: TIMESTAMPTZ (default: `NOW()`)
- `updated_at`: TIMESTAMPTZ (default: `NOW()`)

*Indexes:*
- `idx_users_email`: `(email)`
- `idx_users_org_role`: `(organization_id, role)`

---

### 2.3 `incidents`
Canonical emergency incident records. An incident is the root entity that unifies multiple citizen reports and response tasks.
- `id`: UUID (Primary Key)
- `incident_number`: VARCHAR(50) (UNIQUE, NOT NULL) — e.g., 'RESQ-2026-0041'
- `status`: VARCHAR(50) (NOT NULL, default: `REPORTED`) — Enum: `REPORTED`, `ANALYZING`, `TRIAGED`, `DISPATCHING`, `ACTIVE_RESPONSE`, `RESOLVED`, `CLOSED`, `FALSE_ALARM`
- `priority`: VARCHAR(20) (NOT NULL, default: `MEDIUM`) — Enum: `CRITICAL`, `HIGH`, `MEDIUM`, `LOW`
- `hazard_type`: VARCHAR(50) (NOT NULL) — Enum: `FLOOD`, `LANDSLIDE`, `MEDICAL_EMERGENCY`, `COLLAPSED_STRUCTURE`, `FIRE`, `OTHER`
- `description`: TEXT (NOT NULL)
- `location`: GEOGRAPHY(POINT, 4326) (NOT NULL)
- `district`: VARCHAR(100) (NOT NULL)
- `landmark`: TEXT (NULLABLE)
- `people_affected`: INTEGER (default: 1)
- `trapped_count`: INTEGER (default: 0)
- `injured_count`: INTEGER (default: 0)
- `created_at`: TIMESTAMPTZ (default: `NOW()`)
- `updated_at`: TIMESTAMPTZ (default: `NOW()`)
- `closed_at`: TIMESTAMPTZ (NULLABLE)

*Indexes:*
- `idx_incidents_status`: `(status)`
- `idx_incidents_priority`: `(priority)`
- `idx_incidents_location`: GIST `(location)`

---

### 2.4 `incident_reports`
Individual reports received from citizens, observers, or emergency calls linking to an incident.
- `id`: UUID (Primary Key)
- `incident_id`: UUID (Foreign Key $\rightarrow$ `incidents.id` ON DELETE SET NULL, NULLABLE initially)
- `reporter_name`: VARCHAR(255) (NULLABLE — Anonymous allowed)
- `reporter_phone`: VARCHAR(50) (NULLABLE)
- `raw_text`: TEXT (NOT NULL)
- `reported_location`: GEOGRAPHY(POINT, 4326) (NULLABLE)
- `reported_landmark`: TEXT (NULLABLE)
- `source`: VARCHAR(50) (default: `WEB_ANONYMOUS`) — Enum: `WEB_ANONYMOUS`, `PWA_OFFLINE_SYNC`, `CALL_CENTER`, `SMS_GATEWAY`
- `extracted_entities`: JSONB (default: `{}`)
- `created_at`: TIMESTAMPTZ (default: `NOW()`)

---

### 2.5 `tracking_tokens`
Tokens issued to citizens for tracking progress without requiring authentication.
- `token`: VARCHAR(128) (Primary Key)
- `incident_id`: UUID (Foreign Key $\rightarrow$ `incidents.id` ON DELETE CASCADE, NOT NULL)
- `citizen_phone`: VARCHAR(50) (NULLABLE)
- `expires_at`: TIMESTAMPTZ (NOT NULL)
- `created_at`: TIMESTAMPTZ (default: `NOW()`)

---

### 2.6 `response_tasks`
Discrete executable tasks spawned by an incident. **One incident has many linked tasks.**
- `id`: UUID (Primary Key)
- `incident_id`: UUID (Foreign Key $\rightarrow$ `incidents.id` ON DELETE CASCADE, NOT NULL)
- `parent_task_id`: UUID (Foreign Key $\rightarrow$ `response_tasks.id`, NULLABLE for task dependency chains)
- `task_type`: VARCHAR(50) (NOT NULL) — Enum: `RESCUE_EXTRACTION`, `AMBULANCE_TRANSPORT`, `HOSPITAL_ADMISSION`, `SUPPLY_DELIVERY`, `RELIEF_CAMP_SHELTER`
- `status`: VARCHAR(50) (NOT NULL, default: `PENDING_ASSIGNMENT`) — Enum: `PENDING_ASSIGNMENT`, `ASSIGNED`, `ACCEPTED`, `REJECTED`, `EN_ROUTE`, `ON_SCENE`, `COMPLETED`, `CANCELLED`
- `priority`: VARCHAR(20) (NOT NULL)
- `assigned_organization_id`: UUID (Foreign Key $\rightarrow$ `organizations.id`, NULLABLE)
- `assigned_user_id`: UUID (Foreign Key $\rightarrow$ `users.id`, NULLABLE)
- `target_location`: GEOGRAPHY(POINT, 4326) (NOT NULL)
- `instructions`: TEXT (NULLABLE)
- `assigned_at`: TIMESTAMPTZ (NULLABLE)
- `accepted_at`: TIMESTAMPTZ (NULLABLE)
- `arrived_at`: TIMESTAMPTZ (NULLABLE)
- `completed_at`: TIMESTAMPTZ (NULLABLE)
- `citizen_confirmed_arrival`: BOOLEAN (default: `FALSE`)
- `citizen_confirmed_at`: TIMESTAMPTZ (NULLABLE)
- `created_at`: TIMESTAMPTZ (default: `NOW()`)
- `updated_at`: TIMESTAMPTZ (default: `NOW()`)

*Indexes:*
- `idx_tasks_incident`: `(incident_id)`
- `idx_tasks_status`: `(status)`
- `idx_tasks_assigned_org`: `(assigned_organization_id)`

---

### 2.7 `hospital_capacity`
Deterministic hospital bed and trauma room availability.
- `id`: UUID (Primary Key)
- `organization_id`: UUID (Foreign Key $\rightarrow$ `organizations.id` ON DELETE CASCADE, UNIQUE NOT NULL)
- `total_emergency_beds`: INTEGER (NOT NULL, default: 0)
- `occupied_emergency_beds`: INTEGER (NOT NULL, default: 0)
- `reserved_emergency_beds`: INTEGER (NOT NULL, default: 0)
- `out_of_service_emergency_beds`: INTEGER (NOT NULL, default: 0)
- `total_icu_beds`: INTEGER (NOT NULL, default: 0)
- `occupied_icu_beds`: INTEGER (NOT NULL, default: 0)
- `reserved_icu_beds`: INTEGER (NOT NULL, default: 0)
- `out_of_service_icu_beds`: INTEGER (NOT NULL, default: 0)
- `has_oxygen_facility`: BOOLEAN (default: `TRUE`)
- `has_trauma_center`: BOOLEAN (default: `TRUE`)
- `updated_at`: TIMESTAMPTZ (default: `NOW()`)

*Constraint Checks:*
- `chk_emergency_beds`: `(occupied_emergency_beds + reserved_emergency_beds + out_of_service_emergency_beds <= total_emergency_beds)`
- `chk_icu_beds`: `(occupied_icu_beds + reserved_icu_beds + out_of_service_icu_beds <= total_icu_beds)`

---

### 2.8 `ambulance_status`
Fleet tracking of individual emergency ambulances.
- `id`: UUID (Primary Key)
- `organization_id`: UUID (Foreign Key $\rightarrow$ `organizations.id` ON DELETE CASCADE, NOT NULL)
- `vehicle_plate`: VARCHAR(50) (UNIQUE, NOT NULL)
- `type`: VARCHAR(50) (NOT NULL) — Enum: `BLS` (Basic Life Support), `ALS` (Advanced Life Support), `NEONATAL`, `PATIENT_TRANSPORT`
- `status`: VARCHAR(50) (NOT NULL, default: `AVAILABLE`) — Enum: `AVAILABLE`, `DISPATCHED`, `EN_ROUTE`, `ON_SCENE`, `PATIENT_ON_BOARD`, `MAINTENANCE`, `OFF_DUTY`
- `current_location`: GEOGRAPHY(POINT, 4326) (NOT NULL)
- `current_task_id`: UUID (Foreign Key $\rightarrow$ `response_tasks.id`, NULLABLE)
- `last_telemetry_at`: TIMESTAMPTZ (default: `NOW()`)

---

### 2.9 `resource_inventory`
Disaster relief supplies, medicines, blood reserves, and equipment items.
- `id`: UUID (Primary Key)
- `organization_id`: UUID (Foreign Key $\rightarrow$ `organizations.id` ON DELETE CASCADE, NOT NULL)
- `category`: VARCHAR(50) (NOT NULL) — Enum: `BLOOD_BANK`, `MEDICAL_SUPPLY`, `RESCUE_EQUIPMENT`, `RELIEF_FOOD_WATER`
- `item_code`: VARCHAR(100) (NOT NULL) — e.g., 'BLOOD_O_POS', 'OXYGEN_CYLINDER_D', 'INFLATABLE_BOAT_6P'
- `item_name`: VARCHAR(255) (NOT NULL)
- `unit`: VARCHAR(50) (NOT NULL) — e.g., 'units', 'cylinders', 'kits'
- `total_quantity`: INTEGER (NOT NULL, default: 0)
- `reserved_quantity`: INTEGER (NOT NULL, default: 0)
- `available_quantity`: INTEGER (GENERATED ALWAYS AS (total_quantity - reserved_quantity) STORED)
- `updated_at`: TIMESTAMPTZ (default: `NOW()`)

*Constraint Check:*
- `chk_quantity_valid`: `(reserved_quantity <= total_quantity AND total_quantity >= 0 AND reserved_quantity >= 0)`

---

### 2.10 `resource_reservations`
Time-bounded locks on resources (beds, blood units, gear) during dispatch coordination.
- `id`: UUID (Primary Key)
- `task_id`: UUID (Foreign Key $\rightarrow$ `response_tasks.id` ON DELETE CASCADE, NOT NULL)
- `organization_id`: UUID (Foreign Key $\rightarrow$ `organizations.id` NOT NULL)
- `resource_type`: VARCHAR(50) (NOT NULL) — Enum: `HOSPITAL_EMERGENCY_BED`, `HOSPITAL_ICU_BED`, `INVENTORY_ITEM`
- `resource_id`: UUID (NULLABLE — e.g., references `resource_inventory.id` when applicable)
- `quantity`: INTEGER (NOT NULL, default: 1)
- `status`: VARCHAR(50) (NOT NULL, default: `HOLD`) — Enum: `HOLD`, `CONFIRMED_FULFILLED`, `RELEASED_EXPIRED`, `CANCELLED`
- `expires_at`: TIMESTAMPTZ (NOT NULL) — Typically `NOW() + INTERVAL '30 minutes'`
- `created_at`: TIMESTAMPTZ (default: `NOW()`)
- `fulfilled_at`: TIMESTAMPTZ (NULLABLE)

---

### 2.11 `status_events`
Chronological operational state updates for tasks and incidents.
- `id`: BIGSERIAL (Primary Key)
- `entity_type`: VARCHAR(50) (NOT NULL) — e.g., 'INCIDENT', 'TASK', 'RESOURCE'
- `entity_id`: UUID (NOT NULL)
- `previous_status`: VARCHAR(50) (NULLABLE)
- `new_status`: VARCHAR(50) (NOT NULL)
- `triggered_by_user_id`: UUID (NULLABLE)
- `payload`: JSONB (default: `{}`)
- `timestamp`: TIMESTAMPTZ (default: `NOW()`)

---

### 2.12 `agent_events`
Audit trail of autonomous AI agent reasoning, decisions, and API interactions.
- `id`: BIGSERIAL (Primary Key)
- `incident_id`: UUID (Foreign Key $\rightarrow$ `incidents.id` ON DELETE SET NULL, NULLABLE)
- `agent_name`: VARCHAR(100) (NOT NULL) — e.g., 'IncidentIntelligenceAgent'
- `action_type`: VARCHAR(100) (NOT NULL) — e.g., 'EXTRACTION_COMPLETED', 'TASK_RECOMMENDED'
- `input_context`: JSONB (NOT NULL)
- `output_decision`: JSONB (NOT NULL)
- `confidence_score`: NUMERIC(4, 3) (NULLABLE)
- `execution_time_ms`: INTEGER (NOT NULL)
- `timestamp`: TIMESTAMPTZ (default: `NOW()`)

---

### 2.13 `audit_logs`
Immutable compliance and security record of all authenticated mutations.
- `id`: BIGSERIAL (Primary Key)
- `user_id`: UUID (NULLABLE)
- `action`: VARCHAR(100) (NOT NULL)
- `ip_address`: VARCHAR(45) (NULLABLE)
- `request_route`: VARCHAR(255) (NOT NULL)
- `details`: JSONB (NOT NULL)
- `created_at`: TIMESTAMPTZ (default: `NOW()`)
