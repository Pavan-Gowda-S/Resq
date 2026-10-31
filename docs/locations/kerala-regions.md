# Kerala Regions & Disaster Topography Specification

## 1. Overview

The RESQ simulation and geospatial configuration defaults to **Kerala, India**, reflecting real-world monsoon disaster conditions (floods, river basin inundation, landslide-prone Western Ghats corridors).

---

## 2. Shared Kerala Flood Simulation Nodes

The simulation scenario specified in Section 8 of the Master Architecture mandates the following geographic anchors:

| Node Identifier | Geographic Label | District | Latitude | Longitude | Characteristics |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Village A** | Chalakudy River Basin (Lower) | Thrissur | 10.3120 | 76.3312 | Severe flood inundation; 12 trapped; road access cut off; requires boat extraction. |
| **Village B** | Meppadi / Chooralmala Foothills | Wayanad | 11.5540 | 76.1320 | Landslide hazard; 1 injured with trauma; 3 family members; requires 4x4 + ALS transport. |
| **Village C** | Kuttanad Waterlogged Zone | Alappuzha | 9.5840 | 76.4320 | 2 relief camps; critical supply exhaustion (insulin, clean water, baby food). **Zero cellular connectivity (Offline).** |
| **Hospital A** | General Medical Center | Ernakulam / Angamaly | 10.1960 | 76.3860 | 4 emergency beds available; General trauma care. |
| **Hospital B** | Specialty Cardiac & Trauma Institute | Kochi Metro | 9.9816 | 76.2999 | 2 ICU beds available; Advanced neuro & cardiology services. |
| **Ambulance Hub** | Central District EMS Depot | Thrissur | 10.5276 | 76.2144 | 3 available ambulances (1 ALS, 2 BLS). |
| **Rescue Depot** | Kerala Fire & Rescue Base Alpha | Aluva | 10.1076 | 76.3516 | 4 available teams with motorized rubber boats and divers. |
| **Supplier A** | Kerala State Medical Depot | Kalamassery | 10.0520 | 76.3260 | Stocked with IV fluids, antibiotics, trauma kits. |
| **Supplier B** | Red Cross Regional Blood Bank | Ernakulam | 9.9720 | 76.2840 | O-negative and B-positive reserves. |

---

## 3. Topographical Invariants
- **Rivers & Flood Corridors:** Periyar River, Chalakudy River, Pamba River.
- **Vulnerability Indices:** High risk of bridge submersion during dam shutter openings (Idukki, Idamalayar, Banasura Sagar).
- **Offline Regions:** Village C represents a submerged delta region with downed cell towers, requiring PWA event caching and delayed store-and-forward synchronization.
