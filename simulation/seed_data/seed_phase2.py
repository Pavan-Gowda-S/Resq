"""
Phase 2 Seed Data Script: Organizations and Users
Seeds initial organizations across Kerala and test users for each role.
"""
import asyncio
import sys
from pathlib import Path
from uuid import uuid4

# Add project root to path
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from sqlalchemy import select, text
from geoalchemy2.elements import WKTElement

from backend.app.database import async_engine, AsyncSessionLocal
from backend.app.models import Organization, User
from backend.app.auth.security import get_password_hash


# Kerala districts and sample coordinates
KERALA_LOCATIONS = {
    "Ernakulam": (76.2711, 10.8505),
    "Wayanad": (76.0816, 11.6854),
    "Thrissur": (76.2144, 10.5276),
    "Kottayam": (76.5222, 9.5916),
    "Kozhikode": (75.7804, 11.2588),
}


async def seed_organizations():
    """Seed initial organizations across Kerala districts."""
    print("Seeding organizations...")

    organizations_data = [
        # Hospitals
        {
            "name": "Ernakulam General Hospital",
            "type": "HOSPITAL",
            "registration_number": "KL-HOSP-001",
            "verification_status": "VERIFIED",
            "contact_email": "admin@ernakulam-gh.org",
            "contact_phone": "+919876543201",
            "location": KERALA_LOCATIONS["Ernakulam"],
            "address": "MG Road, Ernakulam, Kerala 682011",
            "district": "Ernakulam",
        },
        {
            "name": "Wayanad District Hospital",
            "type": "HOSPITAL",
            "registration_number": "KL-HOSP-002",
            "verification_status": "VERIFIED",
            "contact_email": "contact@wayanad-dh.org",
            "contact_phone": "+919876543202",
            "location": KERALA_LOCATIONS["Wayanad"],
            "address": "Kalpetta, Wayanad, Kerala 673122",
            "district": "Wayanad",
        },
        {
            "name": "Thrissur Medical College",
            "type": "HOSPITAL",
            "registration_number": "KL-HOSP-003",
            "verification_status": "VERIFIED",
            "contact_email": "tmc@thrissur-medical.org",
            "contact_phone": "+919876543203",
            "location": KERALA_LOCATIONS["Thrissur"],
            "address": "Medical College Road, Thrissur, Kerala 680596",
            "district": "Thrissur",
        },
        # Rescue Organizations
        {
            "name": "Kerala State Fire and Rescue - Ernakulam",
            "type": "RESCUE",
            "registration_number": "KL-RESCUE-001",
            "verification_status": "VERIFIED",
            "contact_email": "fire@ernakulam.gov.in",
            "contact_phone": "+919876543211",
            "location": KERALA_LOCATIONS["Ernakulam"],
            "address": "Fire Station Road, Ernakulam, Kerala 682001",
            "district": "Ernakulam",
        },
        {
            "name": "National Disaster Response Force - Wayanad",
            "type": "RESCUE",
            "registration_number": "KL-RESCUE-002",
            "verification_status": "VERIFIED",
            "contact_email": "ndrf@wayanad.gov.in",
            "contact_phone": "+919876543212",
            "location": KERALA_LOCATIONS["Wayanad"],
            "address": "NDRF Camp, Wayanad, Kerala 673121",
            "district": "Wayanad",
        },
        # Ambulance Providers
        {
            "name": "108 Ambulance Service - Ernakulam",
            "type": "AMBULANCE_PROVIDER",
            "registration_number": "KL-AMB-001",
            "verification_status": "VERIFIED",
            "contact_email": "ambulance@108-ekm.org",
            "contact_phone": "+919876543221",
            "location": KERALA_LOCATIONS["Ernakulam"],
            "address": "108 HQ, Ernakulam, Kerala 682020",
            "district": "Ernakulam",
        },
        {
            "name": "Emergency Medical Services - Thrissur",
            "type": "AMBULANCE_PROVIDER",
            "registration_number": "KL-AMB-002",
            "verification_status": "VERIFIED",
            "contact_email": "ems@thrissur.org",
            "contact_phone": "+919876543222",
            "location": KERALA_LOCATIONS["Thrissur"],
            "address": "EMS Complex, Thrissur, Kerala 680001",
            "district": "Thrissur",
        },
        # Blood Banks
        {
            "name": "Kerala State Blood Bank - Ernakulam",
            "type": "BLOOD_BANK",
            "registration_number": "KL-BLOOD-001",
            "verification_status": "VERIFIED",
            "contact_email": "blood@ernakulam-bb.org",
            "contact_phone": "+919876543231",
            "location": KERALA_LOCATIONS["Ernakulam"],
            "address": "Blood Bank Complex, Ernakulam, Kerala 682018",
            "district": "Ernakulam",
        },
        # Control Rooms
        {
            "name": "State Emergency Operations Center - Thrissur",
            "type": "CONTROL_ROOM",
            "registration_number": "KL-CTRL-001",
            "verification_status": "VERIFIED",
            "contact_email": "seoc@kerala.gov.in",
            "contact_phone": "+919876543241",
            "location": KERALA_LOCATIONS["Thrissur"],
            "address": "SEOC Building, Collectorate, Thrissur, Kerala 680001",
            "district": "Thrissur",
        },
        {
            "name": "District Emergency Operations Center - Ernakulam",
            "type": "CONTROL_ROOM",
            "registration_number": "KL-CTRL-002",
            "verification_status": "VERIFIED",
            "contact_email": "deoc@ernakulam.gov.in",
            "contact_phone": "+919876543242",
            "location": KERALA_LOCATIONS["Ernakulam"],
            "address": "District Collectorate, Ernakulam, Kerala 682011",
            "district": "Ernakulam",
        },
    ]

    async with AsyncSessionLocal() as db:
        created_orgs = {}

        for org_data in organizations_data:
            # Check if organization already exists
            result = await db.execute(
                select(Organization).where(Organization.registration_number == org_data["registration_number"])
            )
            existing = result.scalar_one_or_none()

            if existing:
                print(f"  [OK] Organization already exists: {org_data['name']}")
                created_orgs[org_data["name"]] = existing
                continue

            # Create PostGIS Point from coordinates using WKTElement
            lon, lat = org_data["location"]
            location_wkt = f"POINT({lon} {lat})"

            org = Organization(
                name=org_data["name"],
                type=org_data["type"],
                registration_number=org_data["registration_number"],
                verification_status=org_data["verification_status"],
                contact_email=org_data["contact_email"],
                contact_phone=org_data["contact_phone"],
                location=WKTElement(location_wkt, srid=4326),
                address=org_data["address"],
                district=org_data["district"],
            )

            db.add(org)
            created_orgs[org_data["name"]] = org
            print(f"  + Created: {org_data['name']} ({org_data['type']})")

        await db.commit()
        print(f"[SUCCESS] Seeded {len(created_orgs)} organizations\n")

        return created_orgs


async def seed_users(organizations):
    """Seed test users for each role."""
    print("Seeding users...")

    # Get organizations by type for assignment
    ernakulam_hospital = organizations.get("Ernakulam General Hospital")
    wayanad_hospital = organizations.get("Wayanad District Hospital")
    ernakulam_rescue = organizations.get("Kerala State Fire and Rescue - Ernakulam")
    control_room = organizations.get("State Emergency Operations Center - Thrissur")
    ambulance = organizations.get("108 Ambulance Service - Ernakulam")

    users_data = [
        {
            "email": "admin@resq.system",
            "password": "Admin@123456",
            "full_name": "System Administrator",
            "phone": "+919999999999",
            "role": "SUPERADMIN",
            "organization_id": None,
        },
        {
            "email": "dispatcher@thrissur-ctrl.org",
            "password": "Dispatch@123",
            "full_name": "Rajesh Kumar",
            "phone": "+918888888881",
            "role": "CONTROL_ROOM_DISPATCHER",
            "organization_id": control_room.id if control_room else None,
        },
        {
            "email": "admin@ernakulam-gh.org",
            "password": "Hospital@123",
            "full_name": "Dr. Priya Menon",
            "phone": "+918888888882",
            "role": "ORG_ADMIN",
            "organization_id": ernakulam_hospital.id if ernakulam_hospital else None,
        },
        {
            "email": "doctor@wayanad-dh.org",
            "password": "Doctor@123",
            "full_name": "Dr. Arun Nair",
            "phone": "+918888888883",
            "role": "TRIAGE_DOCTOR",
            "organization_id": wayanad_hospital.id if wayanad_hospital else None,
        },
        {
            "email": "responder@fire-ekm.org",
            "password": "Rescue@123",
            "full_name": "Suresh Babu",
            "phone": "+918888888884",
            "role": "FIELD_RESPONDER",
            "organization_id": ernakulam_rescue.id if ernakulam_rescue else None,
        },
        {
            "email": "driver@108-ekm.org",
            "password": "Ambulance@123",
            "full_name": "Mahesh Varma",
            "phone": "+918888888885",
            "role": "FIELD_RESPONDER",
            "organization_id": ambulance.id if ambulance else None,
        },
    ]

    async with AsyncSessionLocal() as db:
        created_count = 0

        for user_data in users_data:
            # Check if user already exists
            result = await db.execute(
                select(User).where(User.email == user_data["email"])
            )
            existing = result.scalar_one_or_none()

            if existing:
                print(f"  [OK] User already exists: {user_data['email']}")
                continue

            user = User(
                email=user_data["email"],
                password_hash=get_password_hash(user_data["password"]),
                full_name=user_data["full_name"],
                phone=user_data["phone"],
                role=user_data["role"],
                organization_id=user_data["organization_id"],
                is_active=True,
            )

            db.add(user)
            created_count += 1
            print(f"  + Created: {user_data['email']} ({user_data['role']})")

        await db.commit()
        print(f"[SUCCESS] Seeded {created_count} users\n")


async def main():
    """Main seed function."""
    print("=" * 60)
    print("RESQ Phase 2 Seed Data Script")
    print("=" * 60)
    print()

    try:
        # Seed organizations first
        organizations = await seed_organizations()

        # Seed users
        await seed_users(organizations)

        print("=" * 60)
        print("[SUCCESS] Phase 2 seeding completed successfully!")
        print("=" * 60)
        print("\nTest Credentials:")
        print("  Superadmin: admin@resq.system / Admin@123456")
        print("  Dispatcher: dispatcher@thrissur-ctrl.org / Dispatch@123")
        print("  Hospital Admin: admin@ernakulam-gh.org / Hospital@123")
        print("  Doctor: doctor@wayanad-dh.org / Doctor@123")
        print("  Rescue Responder: responder@fire-ekm.org / Rescue@123")
        print("  Ambulance Driver: driver@108-ekm.org / Ambulance@123")
        print()

    except Exception as e:
        print(f"\nError during seeding: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
