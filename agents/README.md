# RESQ AI Agent & Integration System

## 1. Overview
The RESQ Agent Tier is managed via LangGraph and powered by Google Gemini. It coordinates intelligent triage, multi-pathway response planning, and multi-resource matching. It is owned and maintained by **Developer 2 (Integration & AI Agents)**.

---

## 2. Core Operational Rules
1. **No Direct Database Access:** Agents interact solely via typed HTTP calls against the Backend REST API contracts.
2. **Deterministic Safety:** Numerical capacity calculations and resource reservations are strictly delegated to backend validation logic.
3. **Mock Integration:** During Phase 1, use mock backend responses to develop and test LangGraph flows independently before connecting to live endpoints.

---

## 3. Directory Layout
- `orchestrator/`: Central LangGraph supervisor coordinating all nine agents.
- `incident_intelligence/`: Citizen report NLP entity extraction.
- `risk_decision/`: Clinical triage and multi-pathway decision logic.
- `rescue_matching/`: Spatial ranking of rescue teams.
- `hospital_matching/`: Bed matching and ambulance synchronization.
- `route_mobility/`: Hazard-aware transit routing.
- `resource_marketplace/`: Autonomous fair-distribution supply matching.
- `continuity_offline/`: Interrupted workflow recovery and sync replay.
- `verification_audit/`: Discrepancy checks and incident closure audit.
