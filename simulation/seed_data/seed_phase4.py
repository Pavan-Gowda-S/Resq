"""
Phase 4 Seed Data: Hospital Capacity, Ambulance Fleet, and Critical Inventory

Seeds:
- Hospital capacity records for existing Kerala hospitals
- Ambulance fleet (ALS, BLS) with initial locations
- Critical relief inventory (Blood units, Oxygen, Inflatable boats)
"""
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from geoalchemy2.elements import WKTElement

from backend.app.database.config import AsyncSessionLocal
from backend.app.models import Organization, HospitalCapacity, AmbulanceStatus, ResourceInventory


async def seed_phase4_data():
    """Seed Phase 4 resource and capacity data."""
    async with AsyncSessionLocal() as db:
        try:
            # Get existing hospital organizations
            from sqlalchemy import select

            result = await db.execute(
                select(Organization).where(Organization.type == "HOSPITAL")
            )
            hospitals = result.scalars().all()

            if not hospitals:
                print("[ERROR] No hospital organizations found. Run seed_phase2.py first.")
                return

            print(f"[OK] Found {len(hospitals)} hospital organizations")

            # Seed hospital capacity for first 3 hospitals
            capacity_data = [
                {
                    "name": "Ernakulam General Hospital",
                    "total_emergency_beds": 50,
                    "occupied_emergency_beds": 28,
                    "reserved_emergency_beds": 2,
                    "out_of_service_emergency_beds": 5,
                    "total_icu_beds": 20,
                    "occupied_icu_beds": 12,
                    "reserved_icu_beds": 1,
                    "out_of_service_icu_beds": 2,
                    "has_oxygen_facility": True,
                    "has_trauma_center": True,
                },
                {
                    "name": "Wayanad District Hospital",
                    "total_emergency_beds": 30,
                    "occupied_emergency_beds": 15,
                    "reserved_emergency_beds": 0,
                    "out_of_service_emergency_beds": 3,
                    "total_icu_beds": 10,
                    "occupied_icu_beds": 6,
                    "reserved_icu_beds": 0,
                    "out_of_service_icu_beds": 1,
                    "has_oxygen_facility": True,
                    "has_trauma_center": False,
                },
                {
                    "name": "Thrissur Medical College",
                    "total_emergency_beds": 80,
                    "occupied_emergency_beds": 45,
                    "reserved_emergency_beds": 3,
                    "out_of_service_emergency_beds": 7,
                    "total_icu_beds": 30,
                    "occupied_icu_beds": 18,
                    "reserved_icu_beds": 2,
                    "out_of_service_icu_beds": 3,
                    "has_oxygen_facility": True,
                    "has_trauma_center": True,
                },
            ]

            capacity_count = 0
            for i, capacity_spec in enumerate(capacity_data):
                if i >= len(hospitals):
                    break

                hospital = hospitals[i]

                # Check if capacity already exists
                result = await db.execute(
                    select(HospitalCapacity).where(
                        HospitalCapacity.organization_id == hospital.id
                    )
                )
                existing = result.scalar_one_or_none()

                if existing:
                    print(f"[SKIP] Capacity already exists for {hospital.name}")
                    continue

                capacity = HospitalCapacity(
                    organization_id=hospital.id,
                    total_emergency_beds=capacity_spec["total_emergency_beds"],
                    occupied_emergency_beds=capacity_spec["occupied_emergency_beds"],
                    reserved_emergency_beds=capacity_spec["reserved_emergency_beds"],
                    out_of_service_emergency_beds=capacity_spec["out_of_service_emergency_beds"],
                    total_icu_beds=capacity_spec["total_icu_beds"],
                    occupied_icu_beds=capacity_spec["occupied_icu_beds"],
                    reserved_icu_beds=capacity_spec["reserved_icu_beds"],
                    out_of_service_icu_beds=capacity_spec["out_of_service_icu_beds"],
                    has_oxygen_facility=capacity_spec["has_oxygen_facility"],
                    has_trauma_center=capacity_spec["has_trauma_center"],
                )
                db.add(capacity)
                capacity_count += 1

                available_emergency = (
                    capacity_spec["total_emergency_beds"] -
                    capacity_spec["occupied_emergency_beds"] -
                    capacity_spec["reserved_emergency_beds"] -
                    capacity_spec["out_of_service_emergency_beds"]
                )
                available_icu = (
                    capacity_spec["total_icu_beds"] -
                    capacity_spec["occupied_icu_beds"] -
                    capacity_spec["reserved_icu_beds"] -
                    capacity_spec["out_of_service_icu_beds"]
                )
                print(f"[OK] Created capacity for {hospital.name}: {available_emergency} emergency, {available_icu} ICU beds available")

            await db.commit()
            print(f"[OK] Seeded {capacity_count} hospital capacity records")

            # Seed ambulance fleet
            result = await db.execute(
                select(Organization).where(Organization.type == "AMBULANCE_PROVIDER")
            )
            ambulance_orgs = result.scalars().all()

            if not ambulance_orgs:
                print("[WARN] No ambulance provider organizations found")
            else:
                ambulance_fleet = [
                    {
                        "vehicle_plate": "KL-07-AM-1234",
                        "ambulance_type": "ALS",
                        "status": "AVAILABLE",
                        "location": "POINT(76.2711 10.8505)",  # Ernakulam
                        "crew_size": 3,
                    },
                    {
                        "vehicle_plate": "KL-07-AM-5678",
                        "ambulance_type": "BLS",
                        "status": "AVAILABLE",
                        "location": "POINT(76.2144 10.5276)",  # Kochi
                        "crew_size": 2,
                    },
                    {
                        "vehicle_plate": "KL-10-AM-9012",
                        "ambulance_type": "ALS",
                        "status": "AVAILABLE",
                        "location": "POINT(76.2055 11.2588)",  # Kozhikode
                        "crew_size": 3,
                    },
                    {
                        "vehicle_plate": "KL-03-AM-3456",
                        "ambulance_type": "BLS",
                        "status": "AVAILABLE",
                        "location": "POINT(76.9366 8.5241)",  # Thiruvananthapuram
                        "crew_size": 2,
                    },
                    {
                        "vehicle_plate": "KL-08-AM-7890",
                        "ambulance_type": "NEONATAL",
                        "status": "AVAILABLE",
                        "location": "POINT(76.4924 9.3850)",  # Pathanamthitta
                        "crew_size": 3,
                    },
                ]

                ambulance_count = 0
                for ambulance_spec in ambulance_fleet:
                    # Check if ambulance already exists
                    result = await db.execute(
                        select(AmbulanceStatus).where(
                            AmbulanceStatus.vehicle_plate == ambulance_spec["vehicle_plate"]
                        )
                    )
                    existing = result.scalar_one_or_none()

                    if existing:
                        print(f"[SKIP] Ambulance {ambulance_spec['vehicle_plate']} already exists")
                        continue

                    ambulance = AmbulanceStatus(
                        organization_id=ambulance_orgs[0].id,  # Assign to first ambulance provider
                        vehicle_plate=ambulance_spec["vehicle_plate"],
                        type=ambulance_spec["ambulance_type"],
                        status=ambulance_spec["status"],
                        current_location=WKTElement(ambulance_spec["location"], srid=4326),
                        
                    )
                    db.add(ambulance)
                    ambulance_count += 1
                    print(f"[OK] Created ambulance {ambulance_spec['vehicle_plate']} ({ambulance_spec['ambulance_type']})")

                await db.commit()
                print(f"[OK] Seeded {ambulance_count} ambulances")

            # Seed critical relief inventory
            result = await db.execute(
                select(Organization).where(
                    Organization.type.in_(["BLOOD_BANK", "SUPPLIER", "RESCUE"])
                )
            )
            inventory_orgs = result.scalars().all()

            if not inventory_orgs:
                print("[WARN] No inventory organizations found")
            else:
                inventory_items = [
                    {
                        "category": "MEDICAL_SUPPLY",
                        "item_code": "BLOOD-O-POS",
                        "item_name": "O+ Blood Units",
                        "unit": "UNITS",
                        "total_quantity": 50,
                        "reserved_quantity": 5,
                    },
                    {
                        "category": "MEDICAL_SUPPLY",
                        "item_code": "BLOOD-AB-NEG",
                        "item_name": "AB- Blood Units",
                        "unit": "UNITS",
                        "total_quantity": 10,
                        "reserved_quantity": 1,
                    },
                    {
                        "category": "MEDICAL_SUPPLY",
                        "item_code": "OXY-CYL-10L",
                        "item_name": "Oxygen Cylinder 10L",
                        "unit": "PIECES",
                        "total_quantity": 100,
                        "reserved_quantity": 10,
                    },
                    {
                        "category": "EQUIPMENT",
                        "item_code": "BOAT-INFLT-6P",
                        "item_name": "Inflatable Rescue Boat (6 person)",
                        "unit": "PIECES",
                        "total_quantity": 15,
                        "reserved_quantity": 3,
                    },
                    {
                        "category": "RELIEF_MATERIAL",
                        "item_code": "FOOD-DRY-RAT",
                        "item_name": "Dry Food Ration Pack",
                        "unit": "KG",
                        "total_quantity": 500,
                        "reserved_quantity": 50,
                    },
                    {
                        "category": "RELIEF_MATERIAL",
                        "item_code": "WATER-BTL-1L",
                        "item_name": "Bottled Water 1L",
                        "unit": "LITERS",
                        "total_quantity": 2000,
                        "reserved_quantity": 200,
                    },
                ]

                inventory_count = 0
                for item_spec in inventory_items:
                    # Check if item already exists
                    result = await db.execute(
                        select(ResourceInventory).where(
                            ResourceInventory.item_code == item_spec["item_code"]
                        )
                    )
                    existing = result.scalar_one_or_none()

                    if existing:
                        print(f"[SKIP] Inventory item {item_spec['item_code']} already exists")
                        continue

                    # Assign to appropriate organization type
                    if item_spec["category"] == "MEDICAL_SUPPLY" and item_spec["item_code"].startswith("BLOOD"):
                        org = next((o for o in inventory_orgs if o.type == "BLOOD_BANK"), inventory_orgs[0])
                    elif item_spec["category"] == "EQUIPMENT":
                        org = next((o for o in inventory_orgs if o.type == "RESCUE"), inventory_orgs[0])
                    else:
                        org = next((o for o in inventory_orgs if o.type == "SUPPLIER"), inventory_orgs[0])

                    inventory = ResourceInventory(
                        organization_id=org.id,
                        category=item_spec["category"],
                        item_code=item_spec["item_code"],
                        item_name=item_spec["item_name"],
                        unit=item_spec["unit"],
                        total_quantity=item_spec["total_quantity"],
                        reserved_quantity=item_spec["reserved_quantity"],
                    )
                    db.add(inventory)
                    inventory_count += 1

                    available = item_spec["total_quantity"] - item_spec["reserved_quantity"]
                    print(f"[OK] Created inventory: {item_spec['item_name']} ({available} {item_spec['unit']} available)")

                await db.commit()
                print(f"[OK] Seeded {inventory_count} inventory items")

            print("\n" + "="*60)
            print("Phase 4 seed data completed successfully!")
            print(f"- {capacity_count} hospital capacity records")
            print(f"- {ambulance_count} ambulances")
            print(f"- {inventory_count} inventory items")
            print("="*60)

        except Exception as e:
            print(f"[ERROR] Seeding failed: {e}")
            await db.rollback()
            raise


if __name__ == "__main__":
    print("Starting Phase 4 seed data...")
    asyncio.run(seed_phase4_data())
