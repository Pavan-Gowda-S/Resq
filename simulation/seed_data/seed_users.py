"""
Seed Script: Pre-configured Test Users for Team Handoff
Creates/ensures accounts for all key system roles with known credentials.
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from sqlalchemy import select
from backend.app.database import AsyncSessionLocal
from backend.app.models import User, Organization
from backend.app.auth.security import get_password_hash

TEST_USERS = [
    {
        "email": "superadmin@resq.gov.in",
        "password": "Admin@123456",
        "full_name": "State Emergency Director",
        "phone": "+919999900001",
        "role": "SUPERADMIN",
        "org_type": None,
    },
    {
        "email": "dispatcher@ernakulam.resq.gov.in",
        "password": "Dispatch@123",
        "full_name": "Ernakulam DEOC Dispatcher",
        "phone": "+919999900002",
        "role": "CONTROL_ROOM_DISPATCHER",
        "org_type": "CONTROL_ROOM",
    },
    {
        "email": "hospitaladmin@general.resq.gov.in",
        "password": "Hospital@123",
        "full_name": "General Hospital Superintendent",
        "phone": "+919999900003",
        "role": "ORG_ADMIN",
        "org_type": "HOSPITAL",
    },
    {
        "email": "doctor@wayanad.resq.gov.in",
        "password": "Doctor@123",
        "full_name": "Dr. Triage Specialist",
        "phone": "+919999900004",
        "role": "TRIAGE_DOCTOR",
        "org_type": "HOSPITAL",
    },
    {
        "email": "responder01@ndrf.resq.gov.in",
        "password": "Rescue@123",
        "full_name": "NDRF Field Lead",
        "phone": "+919999900005",
        "role": "FIELD_RESPONDER",
        "org_type": "RESCUE",
    },
    {
        "email": "ambulance01@108.resq.gov.in",
        "password": "Ambulance@123",
        "full_name": "108 Paramedic Driver",
        "phone": "+919999900006",
        "role": "FIELD_RESPONDER",
        "org_type": "AMBULANCE_PROVIDER",
    },
]


async def seed_test_users():
    print("[*] Seeding Test Users for Team Handoff...")
    async with AsyncSessionLocal() as session:
        for u in TEST_USERS:
            # Check if user already exists
            result = await session.execute(select(User).where(User.email == u["email"]))
            existing = result.scalar_one_or_none()

            org_id = None
            if u["org_type"]:
                org_res = await session.execute(
                    select(Organization).where(Organization.type == u["org_type"]).limit(1)
                )
                org = org_res.scalar_one_or_none()
                if org:
                    org_id = org.id

            password_hash = get_password_hash(u["password"])

            if existing:
                existing.password_hash = password_hash
                existing.role = u["role"]
                existing.organization_id = org_id
                print(f"  [+] Updated credentials for: {u['email']} ({u['role']})")
            else:
                user = User(
                    email=u["email"],
                    password_hash=password_hash,
                    full_name=u["full_name"],
                    phone=u["phone"],
                    role=u["role"],
                    organization_id=org_id,
                )
                session.add(user)
                print(f"  [+] Created user: {u['email']} ({u['role']})")

        await session.commit()
    print("[SUCCESS] All test users successfully seeded and ready for login.\n")


if __name__ == "__main__":
    asyncio.run(seed_test_users())
