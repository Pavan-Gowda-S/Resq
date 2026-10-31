# RESQ — Architectural Decision Records (ADRs)

## ADR 001: 1-to-Many Relationship Between Incidents and Response Tasks
- **Status:** Accepted
- **Context:** An emergency event often requires simultaneous actions across different emergency sectors (e.g., trapped victim requiring water rescue, immediate ALS ambulance, and an ICU bed).
- **Decision:** Model `incidents` as root coordinating entities that spawn multiple discrete `response_tasks`.
- **Consequence:** Responders and hospitals operate on isolated tasks while control-room dispatchers retain holistic incident status visibility.

---

## ADR 002: Deterministic Capacity Calculations
- **Status:** Accepted
- **Context:** Large Language Models are prone to non-deterministic outputs and hallucinations when evaluating inventory numbers and bed availabilities.
- **Decision:** All capacity queries, bed decrements, and stock calculations are computed strictly by PostgreSQL constraints and FastAPI services. AI agents may rank or select, but never calculate or directly write capacity changes.
- **Formula:**
  $$\text{Available} = \text{Total} - \text{Occupied} - \text{Reserved} - \text{OutOfService}$$

---

## ADR 003: Token-Based Unauthenticated Citizen Tracking
- **Status:** Accepted
- **Context:** Requiring a panicking citizen to register an account or verify an email during an emergency creates unacceptable friction and fatal delays.
- **Decision:** Permit anonymous SOS submissions. Return a cryptographically secure tracking token (UUIDv4/HMAC) allowing the citizen to view live response updates and submit arrival feedback.

---

## ADR 004: Urgent-Need Autonomous Marketplace Allocation
- **Status:** Accepted
- **Context:** Commercial market mechanisms (highest bidder, first-come-first-served) are unethical and dangerous during disaster relief.
- **Decision:** The Resource Marketplace Agent ranks supply distribution strictly by clinical severity, life vulnerability, transit proximity, and verified stock availability.

---

## ADR 005: Causality-Based Offline Event Replay
- **Status:** Accepted
- **Context:** Severe floods and landslides knock out cell towers, causing field teams to operate offline.
- **Decision:** Local devices maintain an append-only event journal. Sync uses vector timestamps and state machine guards. Newest timestamps are never accepted unconditionally over server safety rules.

---

## ADR 006: Postponement of Frontend Development
- **Status:** Accepted
- **Context:** Building UI dashboards before backend contracts, deterministic state machines, and multi-agent coordination logic are stable leads to frequent breaking churn.
- **Decision:** Postpone all frontend development until Backend Phase 6 and Agent Phase 6 gates pass.
