# RESQ Web (all 5 portals)

React + TanStack Start + Tailwind v4 + shadcn UI.

```
bun install
bun run dev   # http://localhost:8080
```

Backend calls go through `src/routes/api/public/resq/$.ts` (proxy to the FastAPI tunnel; change `BASE` there).
Portals work offline using simulated data from `src/lib/resq-data.ts`.

## Who owns what
| Portal | Route file |
|---|---|
| Citizen SOS + tracking | `src/routes/citizen.tsx`, `src/routes/track.$token.tsx` |
| Hospital | `src/routes/hospital.tsx` |
| Rescue team | `src/routes/rescue.tsx` |
| Control room | `src/routes/control.tsx`, `src/components/resq/kerala-map.tsx` |
| Admin | `src/routes/admin.tsx` |
| Shared (nav, login gate, theme) | `src/components/resq/*`, `src/lib/*`, `src/styles.css` |
