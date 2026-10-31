# RESQ — Core API Contracts & Interface Specification

> [!IMPORTANT]
> **Contract Ownership Notice:** The **Backend & Database Developer** owns and implements the authoritative API contracts defined in this document.
> The **Integration & AI Agents Developer** must strictly adhere to these contract schemas and endpoints.
> Neither party may invent uncoordinated endpoint paths or rename schema attributes without an explicit update to this specification.

---

## 1. Global Conventions & Standards

- **Base URL:** `/api/v1`
- **Content-Type:** `application/json` (REST endpoints)
- **Time Format:** ISO 8601 with UTC timezone suffix (`YYYY-MM-DDTHH:MM:SSZ`)
- **Spatial Format:** GeoJSON Point object:
  ```json
  {
    "type": "Point",
    "coordinates": [76.2711, 10.8505] // [longitude, latitude]
  }
  ```
- **Error Response Standard (RFC 7807):**
  ```json
  {
    "error_code": "RESOURCE_INSUFFICIENT",
    "message": "Requested ICU bed count exceeds deterministic available capacity.",
    "details": { "requested": 3, "available": 1 },
    "timestamp": "2026-10-31T12:00:00Z"
  }
  ```

---

## 2. Authentication & Authorization

### 2.1 Login
- **Endpoint:** `POST /api/v1/auth/login`
- **Auth Required:** None
- **Request:**
  ```json
  {
    "email": "doctor@hospital-a.org",
    "password": "SecurePassword123!"
  }
  ```
- **Response (200 OK):**
  ```json
  {
    "access_token": "eyJhbGciOiJIUzI1Ni...",
    "token_type": "bearer",
    "expires_in": 86400,
    "user": {
      "id": "c1f7b022-7901-4475-bce6-3bc5c87ff81e",
      "email": "doctor@hospital-a.org",
      "role": "TRIAGE_DOCTOR",
      "organization_id": "8a3e7b1a-8c76-4b2a-8d19-4a92c3a50e12",
      "organization_name": "Hospital A - General Medical Center"
    }
  }
  ```

---

## 3. Incident Lifecycle APIs

### 3.1 Submit Citizen SOS Report (Unauthenticated)
- **Endpoint:** `POST /api/v1/incidents/report`
- **Auth Required:** None (Public / Anonymous)
- **Request:**
  ```json
  {
    "reporter_name": "Ravi Kumar",
    "reporter_phone": "+919876543210",
    "description": "Rising flood water trapped 4 elderly family members on the terrace. One has severe chest pains.",
    "location": {
      "type": "Point",
      "coordinates": [76.2144, 10.5276]
    },
    "district": "Thrissur",
    "landmark": "Near Chalakudy Bridge, Red house with solar panels",
    "people_affected": 4,
    "source": "WEB_ANONYMOUS"
  }
  ```
- **Response (201 Created):**
  ```json
  {
    "incident_id": "e0a12e84-dfc1-4eb2-a6d5-a6a9b40d6c91",
    "incident_number": "RESQ-2026-1092",
    "status": "REPORTED",
    "tracking_token": "trk_7f8a92b19c28e401bcae3f",
    "tracking_url": "https://resq.org/track/trk_7f8a92b19c28e401bcae3f",
    "message": "Emergency report acknowledged. Intelligent triage has been initiated."
  }
  ```

### 3.2 Track Incident via Token (Citizen Tracking)
- **Endpoint:** `GET /api/v1/incidents/track/{token}`
- **Auth Required:** None (Public via secure token)
- **Response (200 OK):**
  ```json
  {
    "incident_number": "RESQ-2026-1092",
    "status": "ACTIVE_RESPONSE",
    "reported_at": "2026-10-31T07:15:00Z",
    "tasks": [
      {
        "task_id": "b48c3b10-60a1-4328-86d9-f47a61d152c1",
        "task_type": "RESCUE_EXTRACTION",
        "status": "EN_ROUTE",
        "responder_type": "Flood Rescue Boat Team 2",
        "eta_minutes": 14
      },
      {
        "task_id": "d91a2c33-8711-443b-a5d2-00b8e7c169a9",
        "task_type": "AMBULANCE_TRANSPORT",
        "status": "ASSIGNED",
        "responder_type": "Advanced Life Support Ambulance",
        "eta_minutes": 25
      }
    ]
  }
  ```

### 3.3 Propose Multi-Pathway Tasks (Agent / Dispatcher)
- **Endpoint:** `POST /api/v1/incidents/{incident_id}/tasks/propose`
- **Auth Required:** Bearer Token (Role: `CONTROL_ROOM_DISPATCHER` or `SYSTEM_AGENT`)
- **Request:**
  ```json
  {
    "proposals": [
      {
        "task_type": "RESCUE_EXTRACTION",
        "priority": "CRITICAL",
        "target_location": {
          "type": "Point",
          "coordinates": [76.2144, 10.5276]
        },
        "instructions": "Boat extraction for 4 trapped individuals. Priority patient with cardiac symptoms."
      },
      {
        "task_type": "HOSPITAL_ADMISSION",
        "priority": "CRITICAL",
        "target_location": {
          "type": "Point",
          "coordinates": [76.2144, 10.5276]
        },
        "instructions": "ICU bed reservation required for cardiac patient post-extraction."
      }
    ]
  }
  ```
- **Response (201 Created):**
  ```json
  {
    "incident_id": "e0a12e84-dfc1-4eb2-a6d5-a6a9b40d6c91",
    "created_tasks": [
      {
        "id": "b48c3b10-60a1-4328-86d9-f47a61d152c1",
        "task_type": "RESCUE_EXTRACTION",
        "status": "PENDING_ASSIGNMENT"
      },
      {
        "id": "d91a2c33-8711-443b-a5d2-00b8e7c169a9",
        "task_type": "HOSPITAL_ADMISSION",
        "status": "PENDING_ASSIGNMENT"
      }
    ]
  }
  ```

---

## 4. Resource & Dynamic Capacity APIs

### 4.1 Search Hospital Capacity
- **Endpoint:** `GET /api/v1/resources/hospitals/search`
- **Auth Required:** Bearer Token
- **Query Params:** `lat`, `lng`, `radius_km`, `min_icu_available`, `min_emergency_available`
- **Response (200 OK):**
  ```json
  {
    "count": 2,
    "results": [
      {
        "organization_id": "8a3e7b1a-8c76-4b2a-8d19-4a92c3a50e12",
        "hospital_name": "Hospital A - General Medical Center",
        "distance_km": 6.4,
        "available_emergency_beds": 4,
        "available_icu_beds": 0,
        "has_trauma_center": true
      },
      {
        "organization_id": "2b9e6f11-34a8-4c19-9e81-5d76b1049321",
        "hospital_name": "Hospital B - Specialty Cardiac Institute",
        "distance_km": 11.2,
        "available_emergency_beds": 1,
        "available_icu_beds": 2,
        "has_trauma_center": true
      }
    ]
  }
  ```

### 4.2 Create Resource Reservation (Atomic Lock)
- **Endpoint:** `POST /api/v1/resources/reservations`
- **Auth Required:** Bearer Token (`SYSTEM_AGENT` or `CONTROL_ROOM_DISPATCHER`)
- **Request:**
  ```json
  {
    "task_id": "d91a2c33-8711-443b-a5d2-00b8e7c169a9",
    "organization_id": "2b9e6f11-34a8-4c19-9e81-5d76b1049321",
    "resource_type": "HOSPITAL_ICU_BED",
    "quantity": 1,
    "lock_duration_minutes": 30
  }
  ```
- **Response (201 Created):**
  ```json
  {
    "reservation_id": "fe901c23-7744-4890-a812-78d1039840ef",
    "task_id": "d91a2c33-8711-443b-a5d2-00b8e7c169a9",
    "resource_type": "HOSPITAL_ICU_BED",
    "quantity": 1,
    "status": "HOLD",
    "expires_at": "2026-10-31T12:45:00Z"
  }
  ```

---

## 5. Responder Workflow & Confirmation APIs

### 5.1 Accept Task
- **Endpoint:** `PATCH /api/v1/tasks/{task_id}/accept`
- **Auth Required:** Bearer Token (Assigned responder user/org)
- **Response (200 OK):**
  ```json
  {
    "task_id": "b48c3b10-60a1-4328-86d9-f47a61d152c1",
    "status": "ACCEPTED",
    "updated_at": "2026-10-31T12:16:00Z"
  }
  ```

### 5.2 Update Responder Telemetry & Status
- **Endpoint:** `PATCH /api/v1/tasks/{task_id}/status`
- **Auth Required:** Bearer Token
- **Request:**
  ```json
  {
    "status": "ON_SCENE",
    "current_location": {
      "type": "Point",
      "coordinates": [76.2140, 10.5279]
    },
    "note": "Reached site via inflatable rescue boat. Beginning extraction."
  }
  ```

### 5.3 Citizen Arrival Confirmation (via Token)
- **Endpoint:** `POST /api/v1/incidents/track/{token}/confirm-arrival`
- **Auth Required:** None (Validated by token)
- **Request:**
  ```json
  {
    "task_id": "b48c3b10-60a1-4328-86d9-f47a61d152c1",
    "confirmed": true,
    "feedback_comment": "Rescue boat arrived and safely evacuated family members."
  }
  ```

---

## 6. Offline Synchronization API

### 6.1 Synchronize Queued Offline Events
- **Endpoint:** `POST /api/v1/sync/events`
- **Auth Required:** Bearer Token
- **Request:**
  ```json
  {
    "device_id": "dev_boat_team_04",
    "events": [
      {
        "event_id": "89e02c11-9a74-4b9b-9801-ffc723d9a101",
        "entity_type": "TASK",
        "entity_id": "b48c3b10-60a1-4328-86d9-f47a61d152c1",
        "action": "UPDATE_STATUS",
        "payload": { "status": "COMPLETED", "survivors_evacuated": 4 },
        "client_timestamp": "2026-10-31T11:45:20Z"
      }
    ]
  }
  ```
- **Response (200 OK):**
  ```json
  {
    "synced_count": 1,
    "rejected_count": 0,
    "conflicts": []
  }
  ```
