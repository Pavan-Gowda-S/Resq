# RESQ Team Handoff Messages & Antigravity Agent Prompts

This document contains ready-to-send messages for your teammates and the exact **Antigravity prompts** they should paste into their AI coding agents to begin their work immediately.

---

## 1. Message to Send to Friend A (Offline Sync Engineer)

```text
Hey! The RESQ backend and AI agents are live and connected. Everything is pushed to GitHub.

Here is your setup to build the offline queue and synchronization client:

1. Clone & Branch:
   git clone https://github.com/Pavan-Gowda-S/Resq.git
   cd Resq
   git checkout -b feature/offline-sync-engine

2. Live Backend Base URL:
   https://learned-although-fog-juan.trycloudflare.com/api/v1

3. Your Test Responder Account:
   Email: responder01@ndrf.resq.gov.in
   Password: Rescue@123

4. Key Documentation:
   Read `docs/team/HANDOFF.md` in the repo for the full schema and batch sync spec.

5. AI Agent Prompt:
   Open the repository in Antigravity and paste the "Friend A System Prompt" from `docs/team/TEAM_INVITE_AND_PROMPTS.md`. It will guide your agent through the entire offline implementation!
```

---

## 2. Antigravity Prompt for Friend A (Offline Sync Engineer)

> **Copy and paste the entire block below into Antigravity when Friend A starts their session:**

```text
You are pair programming with an engineer working on the RESQ Emergency Coordination Platform.
Your designated domain is: OFFLINE CONTINUITY, EDGE QUEUING, AND SYNC ENGINE.

### Project Context & Architecture:
- Repository: RESQ (Disaster Response Platform for floods and natural disasters).
- Backend: FastAPI, PostGIS, Redis. All 7 phases are completed and verified (101 automated tests passing).
- Live Backend API: https://learned-although-fog-juan.trycloudflare.com/api/v1 (or local via docker compose up -d).
- Documentation: Inspect `docs/team/HANDOFF.md` and `docs/api/api-contracts.md` (Section 6) for authoritative contracts.

### Your Objectives & Responsibilities:
1. Build an Offline Field Sync Engine / Client Library:
   In disaster zones, responders experience prolonged network blackouts. Your client must queue operations locally when offline and reliably sync them in ordered batches when connectivity is restored.

2. Auth & Login Flow:
   - Authenticate via `POST /api/v1/auth/login` using:
     - Username: `responder01@ndrf.resq.gov.in`
     - Password: `Rescue@123`
   - Store and refresh JWT Bearer token for subsequent requests.

3. Offline Batch Synchronization API Contract:
   - Endpoint: `POST /api/v1/sync/events`
   - Header: `Authorization: Bearer <token>`
   - Batch size: 1 to 50 events per batch request.
   - Idempotency: Every event MUST have a client-generated UUIDv4 `event_id`. If network hiccups cause re-transmission, the server uses this ID in `audit_logs` to prevent duplicate processing.
   - Supported Actions:
     * `UPDATE_STATUS` on `TASK`:
       - Status transitions: `ACCEPTED` -> `EN_ROUTE` -> `ON_SCENE` -> `COMPLETED`
     * `UPDATE_LOCATION` on `TASK`:
       - Payload: `{"location": {"type": "Point", "coordinates": [lng, lat]}}`
     * `CONFIRM_ARRIVAL` on `TASK`:
       - Sets arrival confirmation with responder timestamp.
     * `UPDATE_STATUS` on `INCIDENT`:
       - `TRIAGED`, `DISPATCHED`, `RESOLVED`, `CLOSED`

4. What You Should Build in the Codebase:
   - Build a robust client-side offline queue and sync manager (under `frontend/` or a dedicated client library `client/offline/`).
   - Implement persistent local storage for queued events (e.g. SQLite / IndexedDB / robust file-based storage).
   - Implement exponential backoff, retry mechanisms, and network connectivity state detection.
   - Handle partial success responses: the server returns `{"synced_count": N, "rejected_count": M, "conflicts": [...]}`. Successfully synced events must be evicted from the local queue, while conflicts are logged and handled.
   - Build an automated end-to-end integration test or simulation script that:
     1. Disconnects / mocks offline mode.
     2. Generates a queue of status transitions, GPS tracks, and arrival confirmations.
     3. Reconnects and pushes the batch to `POST /api/v1/sync/events`.
     4. Asserts that all events are marked synced with 0 unhandled conflicts.

Inspect `docs/team/HANDOFF.md` to begin. Ask me where you would like to structure the client files before writing them.
```

---

## 3. Message to Send to Friend B (Frontend Developer)

```text
Hey! The RESQ backend and AI agents are live and ready for frontend implementation:

1. Clone & Branch:
   git clone https://github.com/Pavan-Gowda-S/Resq.git
   cd Resq
   git checkout -b feature/frontend-portals

2. Interactive Swagger Docs (Test in Browser):
   https://learned-although-fog-juan.trycloudflare.com/docs

3. Live Backend Base URL:
   https://learned-although-fog-juan.trycloudflare.com/api/v1

4. Real-time WebSocket Endpoints:
   - Live incidents feed: wss://learned-although-fog-juan.trycloudflare.com/ws/incidents?token=<jwt>
   - Live task feed: wss://learned-although-fog-juan.trycloudflare.com/ws/tasks/{task_id}?token=<jwt>

5. Test Logins:
   - Dispatcher (Command & Control): dispatcher@ernakulam.resq.gov.in / Dispatch@123
   - Hospital Admin: hospitaladmin@general.resq.gov.in / Hospital@123
   - NDRF Responder: responder01@ndrf.resq.gov.in / Rescue@123
   - Public Citizen SOS: No login needed! POST /api/v1/incidents/report

6. Full Integration Guide:
   See `docs/team/HANDOFF.md` for schemas, GeoJSON point formats, and rate limits.

7. AI Agent Prompt:
   Open the repository in Antigravity and paste the "Friend B System Prompt" from `docs/team/TEAM_INVITE_AND_PROMPTS.md`.
```

---

## 4. Antigravity Prompt for Friend B (Frontend Developer)

> **Copy and paste the block below into Antigravity when Friend B starts their session:**

```text
You are pair programming with a frontend engineer working on the RESQ Emergency Coordination Platform.
Your designated domain is: FRONTEND WEB & PWA PORTALS.

### Project Context & Architecture:
- Repository: RESQ (Disaster Response Platform for flood and multi-hazard emergencies).
- Backend: FastAPI, PostGIS, Redis Pub/Sub, WebSockets. Live and fully verified.
- Live Backend API: https://learned-although-fog-juan.trycloudflare.com/api/v1
- Interactive OpenAPI Docs: https://learned-although-fog-juan.trycloudflare.com/docs
- Documentation: Inspect `docs/team/HANDOFF.md` for complete API schemas, test logins, and WebSocket specs.

### Portals to Implement (under `frontend/`):
1. Citizen Public SOS & Tracking Portal (No auth required):
   - Emergency SOS submission form (`POST /api/v1/incidents/report`).
   - Captures GPS coordinates, description, number of people affected.
   - Displays live tracking page with map and responder status using tracking token (`GET /api/v1/incidents/track/{tracking_token}`).
   - Citizen arrival confirmation button (`POST /api/v1/incidents/track/{tracking_token}/confirm-arrival`).

2. Dispatcher Command & Control Dashboard (Role: CONTROL_ROOM_DISPATCHER):
   - Auth: `POST /api/v1/auth/login`.
   - Real-time incident list with live WebSocket updates (`/ws/incidents?token=<jwt>`).
   - Incident triage, map view showing spatial duplicate clusters (`/api/v1/incidents/duplicates`).
   - Resource search: available rescue teams (`/api/v1/resources/rescue-teams`) and hospital beds (`/api/v1/resources/hospitals/beds`).
   - Bed reservation trigger (30-minute lock: `POST /api/v1/resources/reservations`).
   - Multi-task proposal and assignment (`POST /api/v1/incidents/{id}/tasks/propose`).

3. Field Responder PWA / View:
   - Task list (assigned to responder).
   - Task acceptance & rejection (`PATCH /api/v1/tasks/{id}/accept`, `PATCH /api/v1/tasks/{id}/reject`).
   - Status transitions (`EN_ROUTE`, `ON_SCENE`, `COMPLETED`).
   - Integration with Friend A's offline queue sync when network drops.

### Technology Stack & Guidelines:
- Recommended: Modern React / Next.js / Vite + Tailwind CSS + Leaflet/MapLibre for geospatial maps.
- Handle WebSockets gracefully with auto-reconnect and 30s ping keep-alives.
- Respect rate limiting: login (10/min), SOS report (5/min). Display polite cooldowns on HTTP 429.

Inspect `docs/team/HANDOFF.md` and check the `frontend/` directory structure to begin.
```
