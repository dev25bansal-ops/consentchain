import asyncio
import os
import sys
from typing import AsyncGenerator
from uuid import uuid4
from datetime import datetime, timedelta, timezone

os.environ["TESTING"] = "1"
os.environ["JWT_SECRET"] = "test-jwt-secret-for-testing-only"
os.environ["API_SECRET_KEY"] = "test-api-secret-key-for-testing"
os.environ["MASTER_ADDRESS"] = "P3E2KO4G7BA6CFH6ICCYRGEIV5QIY5P6F73LEXAMJJUSAMUHURZN3TRGAI"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

import jwt
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.database import Base, DataFiduciaryDB, DataPrincipalDB, ConsentRecordDB, ConsentStatusDB
from core.crypto import CryptoUtils


TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


def create_test_jwt(wallet_address: str = None, principal_id: str = None) -> str:
    """Create a test JWT token for user authentication."""
    from api.main import JWT_SECRET

    payload = {
        "sub": principal_id or str(uuid4()),
        "wallet_address": wallet_address or "B" * 58,
        "type": "access",
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def async_engine():
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def session(async_engine) -> AsyncGenerator[AsyncSession, None]:
    async_session_maker = sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session_maker() as s:
        yield s


@pytest_asyncio.fixture(scope="function")
async def client(session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    from api.main import get_session, app

    async def override_get_session():
        yield session

    app.dependency_overrides[get_session] = override_get_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_fiduciary(session: AsyncSession) -> DataFiduciaryDB:
    api_key = f"test_api_key_{uuid4().hex}"
    api_key_hash = CryptoUtils.hash_api_key(api_key)

    fiduciary = DataFiduciaryDB(
        id=uuid4(),
        name="Test Company Ltd",
        registration_number=f"TEST_{uuid4().hex[:8].upper()}",
        wallet_address="A" * 58,
        contact_email="test@example.com",
        api_key_hash=api_key_hash,
        data_categories='["FINANCIAL", "PERSONAL"]',
        purposes='["KYC Verification", "Service Delivery"]',
        compliance_status="ACTIVE",
        tier="basic",
    )
    session.add(fiduciary)
    await session.commit()
    await session.refresh(fiduciary)

    fiduciary._api_key = api_key
    return fiduciary


@pytest_asyncio.fixture
async def test_principal(session: AsyncSession) -> DataPrincipalDB:
    principal = DataPrincipalDB(
        id=uuid4(),
        wallet_address="B" * 58,
        email_hash=CryptoUtils.sha256(f"principal_{uuid4().hex}@test.com"),
        kyc_verified=True,
    )
    session.add(principal)
    await session.commit()
    await session.refresh(principal)
    return principal


@pytest_asyncio.fixture
async def test_consent(
    session: AsyncSession,
    test_fiduciary: DataFiduciaryDB,
    test_principal: DataPrincipalDB,
) -> ConsentRecordDB:
    from datetime import datetime, timedelta

    consent = ConsentRecordDB(
        id=uuid4(),
        principal_id=test_principal.id,
        fiduciary_id=test_fiduciary.id,
        purpose="Test Purpose",
        data_types='["NAME", "EMAIL"]',
        status=ConsentStatusDB.GRANTED,
        granted_at=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc) + timedelta(days=30),
        consent_hash=CryptoUtils.sha256(f"consent_{uuid4().hex}"),
        on_chain_tx_id=f"tx_{uuid4().hex}",
        on_chain_app_id=12345,
    )
    session.add(consent)
    await session.commit()
    await session.refresh(consent)
    return consent


@pytest.fixture
def auth_headers(test_fiduciary: DataFiduciaryDB) -> dict:
    api_key = getattr(test_fiduciary, "_api_key", "test_api_key")
    return {"Authorization": f"Bearer {api_key}"}


@pytest.fixture
def jwt_headers(test_principal: DataPrincipalDB) -> dict:
    token = create_test_jwt(
        wallet_address=test_principal.wallet_address, principal_id=str(test_principal.id)
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def mock_redis():
    """Provide a mocked Redis client for tests."""
    from unittest.mock import AsyncMock

    mock = AsyncMock()
    mock.ping = AsyncMock(return_value=True)
    mock.get = AsyncMock(return_value=None)
    mock.setex = AsyncMock(return_value=True)
    mock.delete = AsyncMock(return_value=1)
    mock.keys = AsyncMock(return_value=[])
    mock.incrby = AsyncMock(return_value=1)
    mock.ttl = AsyncMock(return_value=60)
    mock.close = AsyncMock()
    return mock
