# RESQ Multi-Portal Frontend Team Guide

Welcome to the **RESQ Disaster Coordination Frontend**.

All 5 emergency portals are unified in this directory with a shared design system, dark emergency theme, and live backend proxy.

---

## Quick Start (Run Locally)

```bash
cd frontend

# Using Bun (Recommended - instant start)
bun install
bun run dev

# OR using NPM
npm install
npm run dev
```

App runs at: **http://localhost:3000** (or port specified in terminal).

---

## Team Portal Assignments & Route Ownership

Each team member owns their dedicated portal file in `src/routes/`. You can work independently without merge conflicts!

| Portal | Team Member | File to Edit | Key Features to Implement |
| :--- | :--- | :--- | :--- |
| **🏥 Hospital Portal** | Megha / Healthcare Lead | `src/routes/hospital.tsx` | ICU/Trauma bed steppers, Oxygen status, admitting incoming ambulances |
| **🚤 Rescue Team** | Responder Lead | `src/routes/rescue.tsx` | Target victim coordinates, rescue status toggles, casualty logger |
| **🚨 District Control Room** | Operations Lead | `src/routes/control.tsx` & `src/components/resq/kerala-map.tsx` | War room map, AI agent perception feed, live incident telemetry |
| **🛡️ System Admin** | Platform Lead | `src/routes/admin.tsx` | Organization verification, audit ledger, system health |
| **📍 Citizen SOS & Tracking** | Citizen Lead | `src/routes/citizen.tsx` & `src/routes/track.$token.tsx` | Voice SOS, photo upload, live GPS, 5-stage status tracking |

---

## Live Backend API Connection

The frontend automatically proxies requests to the live Cloudflare backend tunnel:
`https://tied-politics-supervision-blink.trycloudflare.com/api/v1`

Configuration file: `src/routes/api/public/resq/$.ts`
