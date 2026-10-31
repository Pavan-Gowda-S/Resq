# Geospatial Routing & Map Hazard Data Specification

## 1. Coordinate Reference Systems (CRS)

- **Standard Internal Representation:** EPSG:4326 (WGS84 Latitude/Longitude).
- **Spatial Queries:** PostGIS geography types calculate ellipsoidal distances in meters using Great Circle calculations.

---

## 2. Hazard Zones & Passability States

Road corridors and water crossings possess dynamic passability states stored and evaluated by the `Route & Mobility Agent`:

```json
{
  "hazard_id": "haz_kerala_periyar_bridge_01",
  "name": "Marthanda Varma Bridge Submersion",
  "location": {
    "type": "LineString",
    "coordinates": [
      [76.3516, 10.1076],
      [76.3530, 10.1085]
    ]
  },
  "hazard_type": "FLOOD_SUBMERSION",
  "water_depth_cm": 140,
  "status": "IMPASSABLE_FOR_WHEELED_VEHICLES",
  "passable_for_boat": true,
  "verified_by": "Kerala State Disaster Management Authority (KSDMA)",
  "reported_at": "2026-10-31T06:00:00Z"
}
```

---

## 3. Mobility Rules

1. **Rule of Verification:** A route is never flagged `SAFE` merely because standard map APIs (OSRM, OpenStreetMap) produce a shortest path. If a segment intersects an active hazard polygon, it must be flagged with `RESTRICTED_ACCESS`.
2. **Vehicle Clearance Filtering:**
   - Standard Ambulance (BLS): Max water wading depth $25\text{ cm}$.
   - Heavy 4x4 / Unimog: Max water wading depth $80\text{ cm}$.
   - Rescue Boats: Operates only in waterways and inundated zones where water depth $>60\text{ cm}$.
