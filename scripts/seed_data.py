"""
Seed Data Script for ConsentChain
Populates the development database with test data.

Usage:
    python scripts/seed_data.py

Environment Variables:
    DATABASE_URL - Database connection string (default: SQLite for testing)
    SEED_COUNT_CONSENTS - Number of consents to create (default: 50)
    SEED_COUNT_PRINCIPALS - Number of principals to create (default: 10)
    SEED_COUNT_FIDUCIARIES - Number of fiduciaries to create (default: 3)
    SEED_COUNT_AUDIT_LOGS - Number of audit logs to create (default: 20)
    SEED_COUNT_GRIEVANCES - Number of grievances to create (default: 5)
"""

import asyncio
import hashlib
import json
import os
import sys
import random
from datetime import datetime, timezone, timedelta
from uuid import uuid4

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

from api.database import (
    Base,
    DataPrincipalDB,
    DataFiduciaryDB,
    ConsentRecordDB,
    ConsentEventDB,
    ConsentStatusDB,
    EventTypeDB,
    AuditLogDB,
)

# Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./consentchain_seed.db")
SEED_COUNT_PRINCIPALS = int(os.getenv("SEED_COUNT_PRINCIPALS", "10"))
SEED_COUNT_FIDUCIARIES = int(os.getenv("SEED_COUNT_FIDUCIARIES", "3"))
SEED_COUNT_CONSENTS = int(os.getenv("SEED_COUNT_CONSENTS", "50"))
SEED_COUNT_AUDIT_LOGS = int(os.getenv("SEED_COUNT_AUDIT_LOGS", "20"))
SEED_COUNT_GRIEVANCES = int(os.getenv("SEED_COUNT_GRIEVANCES", "5"))

# Test data
PURPOSES = [
    "identity_verification",
    "credit_assessment",
    "healthcare_services",
    "marketing_analytics",
    "fraud_detection",
    "personalized_recommendations",
    "regulatory_compliance",
    "research_development",
]

DATA_TYPES = [
    ["identity", "contact"],
    ["financial", "identity"],
    ["health", "identity"],
    ["behavioral", "demographic"],
    ["biometric", "identity"],
    ["location", "device"],
    ["transaction", "financial"],
    ["communication", "contact"],
]

GRIEVANCE_TYPES = [
    "unauthorized_access",
    "data_breach",
    "consent_violation",
    "deletion_failure",
    "accuracy_dispute",
]

GRIEVANCE_STATUSES = ["PENDING", "ACKNOWLEDGED", "IN_PROGRESS", "RESOLVED", "ESCALATED"]
GRIEVANCE_PRIORITIES = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]

ACTIONS = [
    "CONSENT_CREATE",
    "CONSENT_VIEW",
    "CONSENT_REVOKE",
    "CONSENT_MODIFY",
    "DATA_ACCESS",
    "DATA_EXPORT",
    "DATA_DELETE",
    "LOGIN",
    "LOGOUT",
    "REGISTRATION",
]

RESOURCE_TYPES = ["consent", "principal", "fiduciary", "audit_log", "grievance"]


def generate_wallet_address() -> str:
    """Generate a random Algorand-like wallet address."""
    return "ALGO" + hashlib.sha256(str(uuid4()).encode()).hexdigest()[:54]


def generate_consent_hash() -> str:
    """Generate a random consent hash."""
    return hashlib.sha256(str(uuid4()).encode()).hexdigest()


def random_past_datetime(days_back: int = 90) -> datetime:
    """Generate a random datetime within the past N days."""
    days_ago = random.randint(0, days_back)
    hours_ago = random.randint(0, 23)
    return datetime.now(timezone.utc) - timedelta(days=days_ago, hours=hours_ago)


async def seed_principals(session: AsyncSession, count: int) -> list[DataPrincipalDB]:
    """Create test data principals."""
    print(f"  Creating {count} data principals...")
    principals = []

    for i in range(count):
        wallet = generate_wallet_address()
        principal = DataPrincipalDB(
            wallet_address=wallet,
            email_hash=hashlib.sha256(f"principal_{i}@test.com".encode()).hexdigest(),
            phone_hash=hashlib.sha256(f"+919999999{i:04d}".encode()).hexdigest() if i % 3 == 0 else None,
            kyc_verified=random.choice([True, True, True, False]),  # 75% verified
            preferred_language=random.choice(["en", "hi", "ta", "bn"]),
        )
        session.add(principal)
        principals.append(principal)

    await session.flush()
    print(f"  ✓ Created {len(principals)} principals")
    return principals


async def seed_fiduciaries(session: AsyncSession, count: int) -> list[DataFiduciaryDB]:
    """Create test data fiduciaries."""
    print(f"  Creating {count} data fiduciaries...")
    fiduciaries = []

    fiduciary_names = [
        ("HealthFirst Analytics", "HFA-2024-001"),
        ("FinSecure Services", "FSS-2024-002"),
        ("DataTrust Solutions", "DTS-2024-003"),
        ("MediCare Digital", "MCD-2024-004"),
        ("SmartBank AI", "SBA-2024-005"),
    ]

    for i in range(min(count, len(fiduciary_names))):
        name, reg_num = fiduciary_names[i]
        api_key = f"test_api_key_{uuid4().hex[:32]}"
        fiduciary = DataFiduciaryDB(
            name=name,
            registration_number=reg_num,
            wallet_address=generate_wallet_address(),
            contact_email=f"contact@{name.lower().replace(' ', '')}.com",
            api_key_hash=hashlib.sha256(api_key.encode()).hexdigest(),
            data_categories=json.dumps(random.sample(DATA_TYPES, min(3, len(DATA_TYPES)))),
            purposes=json.dumps(random.sample(PURPOSES, min(4, len(PURPOSES)))),
            compliance_status="ACTIVE",
            tier=random.choice(["free", "starter", "professional"]),
        )
        session.add(fiduciary)
        fiduciaries.append(fiduciary)

    await session.flush()
    print(f"  ✓ Created {len(fiduciaries)} fiduciaries")
    return fiduciaries


async def seed_consents(
    session: AsyncSession,
    count: int,
    principals: list[DataPrincipalDB],
    fiduciaries: list[DataFiduciaryDB],
) -> list[ConsentRecordDB]:
    """Create test consent records."""
    print(f"  Creating {count} consent records...")
    consents = []

    status_weights = [
        (ConsentStatusDB.GRANTED, 60),
        (ConsentStatusDB.REVOKED, 15),
        (ConsentStatusDB.EXPIRED, 15),
        (ConsentStatusDB.MODIFIED, 7),
        (ConsentStatusDB.PENDING, 3),
    ]
    statuses = [s for s, w in status_weights for _ in range(w)]

    for i in range(count):
        principal = random.choice(principals)
        fiduciary = random.choice(fiduciaries)
        status = random.choice(statuses)
        granted_at = random_past_datetime()
        duration_days = random.choice([30, 90, 180, 365, 730])

        consent = ConsentRecordDB(
            principal_id=principal.id,
            fiduciary_id=fiduciary.id,
            purpose=random.choice(PURPOSES),
            data_types=json.dumps(random.choice(DATA_TYPES)),
            status=status,
            granted_at=granted_at if status != ConsentStatusDB.PENDING else None,
            expires_at=granted_at + timedelta(days=duration_days) if granted_at else None,
            revoked_at=granted_at + timedelta(days=random.randint(1, 30)) if status == ConsentStatusDB.REVOKED else None,
            on_chain_tx_id=f"tx_{uuid4().hex[:16]}" if status != ConsentStatusDB.PENDING else None,
            on_chain_app_id=random.choice([757755252, 757755253, 0]),
            consent_hash=generate_consent_hash(),
            extra_data=json.dumps({"seed": True, "batch": "seed_data"}),
        )
        session.add(consent)
        consents.append(consent)

    await session.flush()
    print(f"  ✓ Created {len(consents)} consents")
    return consents


async def seed_consent_events(
    session: AsyncSession,
    consents: list[ConsentRecordDB],
) -> list[ConsentEventDB]:
    """Create consent events for audit trail."""
    print(f"  Creating consent events...")
    events = []

    event_type_map = {
        ConsentStatusDB.GRANTED: EventTypeDB.CONSENT_GRANTED,
        ConsentStatusDB.REVOKED: EventTypeDB.CONSENT_REVOKED,
        ConsentStatusDB.MODIFIED: EventTypeDB.CONSENT_MODIFIED,
        ConsentStatusDB.EXPIRED: EventTypeDB.CONSENT_EXPIRY,
        ConsentStatusDB.PENDING: None,
    }

    for consent in consents:
        event_type = event_type_map.get(consent.status)
        if event_type is None:
            continue

        event = ConsentEventDB(
            consent_id=consent.id,
            event_type=event_type,
            actor=consent.principal_id.hex[:12] if hasattr(consent.principal_id, 'hex') else str(consent.principal_id)[:12],
            actor_type="principal",
            previous_status=ConsentStatusDB.PENDING,
            new_status=consent.status,
            tx_id=consent.on_chain_tx_id,
            extra_data=json.dumps({"seed": True}),
        )
        session.add(event)
        events.append(event)

    await session.flush()
    print(f"  ✓ Created {len(events)} consent events")
    return events


async def seed_audit_logs(
    session: AsyncSession,
    count: int,
    principals: list[DataPrincipalDB],
    fiduciaries: list[DataFiduciaryDB],
    consents: list[ConsentRecordDB],
) -> list[AuditLogDB]:
    """Create test audit log entries."""
    print(f"  Creating {count} audit log entries...")
    audit_logs = []

    for i in range(count):
        principal = random.choice(principals)
        fiduciary = random.choice(fiduciaries)
        consent = random.choice(consents) if consents else None

        log = AuditLogDB(
            principal_id=principal.id,
            fiduciary_id=fiduciary.id,
            action=random.choice(ACTIONS),
            resource_type=random.choice(RESOURCE_TYPES),
            resource_id=consent.id if consent else principal.id,
            ip_address=f"192.168.{random.randint(1, 255)}.{random.randint(1, 255)}",
            user_agent=random.choice([
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) ConsentChain/1.1.0",
                "ConsentChain-Mobile/1.0.0 (iOS 17.0)",
                "ConsentChain-Mobile/1.0.0 (Android 14)",
                "curl/8.0.0",
                "PostmanRuntime/7.36.0",
            ]),
            on_chain_reference=f"tx_{uuid4().hex[:16]}" if random.random() > 0.3 else None,
            verified=random.choice([True, True, True, False]),
        )
        session.add(log)
        audit_logs.append(log)

    await session.flush()
    print(f"  ✓ Created {len(audit_logs)} audit logs")
    return audit_logs


async def seed_grievances(
    session: AsyncSession,
    count: int,
    principals: list[DataPrincipalDB],
    fiduciaries: list[DataFiduciaryDB],
    consents: list[ConsentRecordDB],
) -> list:
    """Create test grievance records.

    Note: Grievance models are defined in api/routes/grievance.py.
    We insert raw SQL for flexibility.
    """
    print(f"  Creating {count} grievance records...")

    # Try to import the grievance model if available
    try:
        from api.database import GrievanceDB, GrievanceTypeDB, GrievanceStatusDB, GrievancePriorityDB

        grievances = []
        for i in range(count):
            principal = random.choice(principals)
            fiduciary = random.choice(fiduciaries)
            consent = random.choice(consents) if consents and random.random() > 0.3 else None
            status = random.choice(GRIEVANCE_STATUSES)
            created_at = random_past_datetime()

            grievance = GrievanceDB(
                principal_id=principal.id,
                fiduciary_id=fiduciary.id,
                grievance_type=random.choice(GRIEVANCE_TYPES),
                subject=f"Test grievance #{i+1}: {random.choice(['Data misuse concern', 'Consent not honored', 'Unable to delete data', 'Unauthorized sharing', 'Incorrect data'])}",
                description=f"This is a seeded test grievance to validate the grievance management system. Created for testing purposes with random data to simulate real-world scenarios.",
                status=status,
                priority=random.choice(GRIEVANCE_PRIORITIES),
                consent_id=consent.id if consent else None,
                created_at=created_at,
                expected_resolution_date=created_at + timedelta(days=30),
                resolution=f"Resolved: This test grievance was created for validation purposes." if status == "RESOLVED" else None,
                resolution_date=created_at + timedelta(days=random.randint(1, 25)) if status == "RESOLVED" else None,
            )
            session.add(grievance)
            grievances.append(grievance)

        await session.flush()
        print(f"  ✓ Created {len(grievances)} grievances")
        return grievances

    except ImportError:
        # Grievance model not available in database.py, use raw SQL
        print("  Note: Grievance model not found in database.py, creating via raw SQL...")
        from sqlalchemy import text

        grievance_data = []
        for i in range(count):
            principal = random.choice(principals)
            fiduciary = random.choice(fiduciaries)
            consent = random.choice(consents) if consents and random.random() > 0.3 else None
            status = random.choice(GRIEVANCE_STATUSES)
            created_at = random_past_datetime()
            grievance_id = str(uuid4())

            grievance_data.append({
                "id": grievance_id,
                "principal_id": str(principal.id),
                "fiduciary_id": str(fiduciary.id),
                "consent_id": str(consent.id) if consent else None,
                "grievance_type": random.choice(GRIEVANCE_TYPES),
                "subject": f"Test grievance #{i+1}: Data concern",
                "description": "This is a seeded test grievance for validation.",
                "status": status,
                "priority": random.choice(GRIEVANCE_PRIORITIES),
                "created_at": created_at.isoformat(),
                "expected_resolution_date": (created_at + timedelta(days=30)).isoformat(),
                "resolution": "Resolved for testing" if status == "RESOLVED" else None,
            })

        # Insert grievances using raw SQL
        for gd in grievance_data:
            try:
                await session.execute(text("""
                    INSERT INTO grievances (
                        id, principal_id, fiduciary_id, consent_id,
                        grievance_type, subject, description,
                        status, priority, created_at,
                        expected_resolution_date, resolution
                    ) VALUES (
                        :id, :principal_id, :fiduciary_id, :consent_id,
                        :grievance_type, :subject, :description,
                        :status, :priority, :created_at,
                        :expected_resolution_date, :resolution
                    ) ON CONFLICT DO NOTHING
                """), gd)
            except Exception as e:
                print(f"  Warning: Could not insert grievance: {e}")

        await session.flush()
        print(f"  ✓ Attempted to create {count} grievances")
        return grievance_data


async def seed_database():
    """Main seed function."""
    print("=" * 60)
    print("ConsentChain - Database Seed Script")
    print("=" * 60)
    print(f"Database: {DATABASE_URL}")
    print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    print("-" * 60)

    # Create async engine and session
    if "sqlite" in DATABASE_URL:
        engine = create_async_engine(
            DATABASE_URL,
            echo=False,
            connect_args={"check_same_thread": False},
        )
    else:
        engine = create_async_engine(
            DATABASE_URL,
            echo=False,
            pool_size=5,
            max_overflow=10,
        )

    async_session_factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    # Create tables if they don't exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✓ Database tables verified/created")
    print("-" * 60)

    async with async_session_factory() as session:
        # Seed data in dependency order
        principals = await seed_principals(session, SEED_COUNT_PRINCIPALS)
        fiduciaries = await seed_fiduciaries(session, SEED_COUNT_FIDUCIARIES)
        consents = await seed_consents(session, SEED_COUNT_CONSENTS, principals, fiduciaries)
        await seed_consent_events(session, consents)
        audit_logs = await seed_audit_logs(session, SEED_COUNT_AUDIT_LOGS, principals, fiduciaries, consents)
        grievances = await seed_grievances(session, SEED_COUNT_GRIEVANCES, principals, fiduciaries, consents)

        # Commit all changes
        await session.commit()

    # Print summary
    print("-" * 60)
    print("Seed Summary:")
    print(f"  Data Principals:    {SEED_COUNT_PRINCIPALS}")
    print(f"  Data Fiduciaries:   {len(fiduciaries)}")
    print(f"  Consent Records:    {SEED_COUNT_CONSENTS}")
    print(f"  Audit Logs:         {SEED_COUNT_AUDIT_LOGS}")
    print(f"  Grievances:         {SEED_COUNT_GRIEVANCES}")
    print("-" * 60)
    print("✓ Database seeding complete!")
    print("=" * 60)

    await engine.dispose()


if __name__ == "__main__":
    try:
        asyncio.run(seed_database())
    except KeyboardInterrupt:
        print("\n\nSeeding cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Seeding failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
