"""
Automatic database schema bootstrap and seed script for RESQ.
Ensures all 13 tables, core emergency organizations, hospital capacities,
and verified role-based accounts exist automatically on application startup.
"""
import uuid
import logging
from sqlalchemy import select
from geoalchemy2.elements import WKTElement

from backend.app.database.config import async_engine, AsyncSessionLocal
from backend.app.database.base import Base
import backend.app.models
from backend.app.models import (
    Organization,
    HospitalCapacity,
    User,
    AmbulanceStatus,
)
from backend.app.auth.security import get_password_hash

logger = logging.getLogger("resq.bootstrap")

# Standard fixed UUIDs matching frontend DEFAULT_* constants
DEFAULT_HOSPITAL_ID = uuid.UUID("1c11ce50-f018-41ee-8765-49cd8577578e")
DEFAULT_RESCUE_ORG_ID = uuid.UUID("3d8599f7-10a0-46fa-a061-315b3b7a8a8f")
DEFAULT_CONTROL_ORG_ID = uuid.UUID("4a054031-717c-4523-b776-a50fae58354e")


async def bootstrap_database():
    """Create all tables and seed required system state."""
    logger.info("Initializing database schema...")
    try:
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("[+] RESQ schema verified / tables created successfully")
    except Exception as e:
        print(f"[-] Database table creation error: {e}")
        return

    # Seed core entities
    try:
        async with AsyncSessionLocal() as session:
            # 1. Wayanad District Hospital
            res = await session.execute(select(Organization).where(Organization.id == DEFAULT_HOSPITAL_ID))
            hosp = res.scalar_one_or_none()
            if not hosp:
                hosp = Organization(
                    id=DEFAULT_HOSPITAL_ID,
                    name="Wayanad District Hospital",
                    type="HOSPITAL",
                    registration_number="KL-HOSP-WAYANAD-01",
                    verification_status="VERIFIED",
                    contact_email="contact@wayanad-dh.org",
                    contact_phone="+919876543202",
                    location=WKTElement("POINT(76.0816 11.6854)", srid=4326),
                    address="Kalpetta, Wayanad, Kerala 673122",
                    district="Wayanad",
                )
                session.add(hosp)
                print("[+] Seeded Hospital: Wayanad District Hospital")

            # 2. NDRF Wayanad Rapid Wing
            res = await session.execute(select(Organization).where(Organization.id == DEFAULT_RESCUE_ORG_ID))
            rescue = res.scalar_one_or_none()
            if not rescue:
                rescue = Organization(
                    id=DEFAULT_RESCUE_ORG_ID,
                    name="NDRF Wayanad Rapid Wing",
                    type="RESCUE",
                    registration_number="KL-RESC-WAYANAD-01",
                    verification_status="VERIFIED",
                    contact_email="wayanad@ndrf.gov.in",
                    contact_phone="+919876543212",
                    location=WKTElement("POINT(76.1300 11.6000)", srid=4326),
                    address="Vythiri Camp, Wayanad, Kerala 673576",
                    district="Wayanad",
                )
                session.add(rescue)
                print("[+] Seeded Rescue Org: NDRF Wayanad Rapid Wing")

            # 3. Wayanad DEOC Control Room
            res = await session.execute(select(Organization).where(Organization.id == DEFAULT_CONTROL_ORG_ID))
            control = res.scalar_one_or_none()
            if not control:
                control = Organization(
                    id=DEFAULT_CONTROL_ORG_ID,
                    name="Wayanad DEOC District Control Room",
                    type="CONTROL_ROOM",
                    registration_number="KL-CTRL-WAYANAD-01",
                    verification_status="VERIFIED",
                    contact_email="deoc.wayanad@kerala.gov.in",
                    contact_phone="+919876543222",
                    location=WKTElement("POINT(76.1000 11.6500)", srid=4326),
                    address="Collectorate, Kalpetta, Wayanad 673122",
                    district="Wayanad",
                )
                session.add(control)
                print("[+] Seeded Control Room: Wayanad DEOC")

            await session.flush()

            # 4. Hospital Capacity for Wayanad District Hospital
            cap_res = await session.execute(
                select(HospitalCapacity).where(HospitalCapacity.organization_id == DEFAULT_HOSPITAL_ID)
            )
            cap = cap_res.scalar_one_or_none()
            if not cap:
                cap = HospitalCapacity(
                    organization_id=DEFAULT_HOSPITAL_ID,
                    total_emergency_beds=30,
                    occupied_emergency_beds=15,
                    reserved_emergency_beds=0,
                    out_of_service_emergency_beds=3,
                    total_icu_beds=10,
                    occupied_icu_beds=6,
                    reserved_icu_beds=0,
                    out_of_service_icu_beds=1,
                    has_oxygen_facility=True,
                    has_trauma_center=True,
                )
                session.add(cap)
                print("[+] Seeded Hospital Capacity: 30 Emergency Beds, 10 ICU Beds (4 available)")

            # 5. Core Users
            users_to_seed = [
                {
                    "email": "admin@resq.system",
                    "password": "Admin@123456",
                    "full_name": "RESQ System Administrator",
                    "phone": "+919999900000",
                    "role": "SUPERADMIN",
                    "org_id": DEFAULT_HOSPITAL_ID,
                },
                {
                    "email": "doctor@wayanad.resq.gov.in",
                    "password": "Doctor@123",
                    "full_name": "Dr. Triage Specialist",
                    "phone": "+919999900004",
                    "role": "TRIAGE_DOCTOR",
                    "org_id": DEFAULT_HOSPITAL_ID,
                },
                {
                    "email": "responder01@ndrf.resq.gov.in",
                    "password": "Rescue@123",
                    "full_name": "NDRF Field Lead",
                    "phone": "+919999900005",
                    "role": "FIELD_RESPONDER",
                    "org_id": DEFAULT_RESCUE_ORG_ID,
                },
                {
                    "email": "dispatcher@ernakulam.resq.gov.in",
                    "password": "Dispatch@123",
                    "full_name": "District Control Room Dispatcher",
                    "phone": "+919999900002",
                    "role": "CONTROL_ROOM_DISPATCHER",
                    "org_id": DEFAULT_CONTROL_ORG_ID,
                },
            ]

            for u in users_to_seed:
                u_res = await session.execute(select(User).where(User.email == u["email"]))
                existing_user = u_res.scalar_one_or_none()
                pwd_hash = get_password_hash(u["password"])
                if not existing_user:
                    new_user = User(
                        email=u["email"],
                        password_hash=pwd_hash,
                        full_name=u["full_name"],
                        phone=u["phone"],
                        role=u["role"],
                        organization_id=u["org_id"],
                        is_active=True,
                    )
                    session.add(new_user)
                    print(f"[+] Created user account: {u['email']} ({u['role']})")
                else:
                    existing_user.password_hash = pwd_hash
                    existing_user.role = u["role"]
                    existing_user.organization_id = u["org_id"]

            await session.commit()
            print("[+] Database bootstrap and seeding completed successfully.")
    except Exception as e:
        print(f"[-] Database seed error: {e}")
