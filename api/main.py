from fastapi import FastAPI, HTTPException, Depends, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from contextlib import asynccontextmanager
from typing import Optional, List
from datetime import datetime, timedelta
from uuid import UUID
import json
import os
from dotenv import load_dotenv

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from api.schemas import (
    APIResponse,
    ConsentCreateRequest,
    ConsentRevokeRequest,
    ConsentModifyRequest,
    ConsentVerifyRequest,
    ConsentQueryRequest,
    FiduciaryRegisterRequest,
    AuditQueryRequest,
    ComplianceReportRequest,
    BatchConsentCreateRequest,
    WebhookSubscribeRequest,
)
from api.database import Base
from api.services import ConsentService, AuditService, ComplianceService
from core.crypto import CryptoUtils
from core.models import ConsentRecord, ConsentEvent, AuditLog, ComplianceReport
from contracts.client import AlgorandClient

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql+asyncpg://user:password@localhost:5432/consentchain"
)
CONSENT_APP_ID = int(os.getenv("CONSENT_REGISTRY_APP_ID", "0"))
AUDIT_APP_ID = int(os.getenv("AUDIT_APP_ID", "0"))

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

algorand_client: Optional[AlgorandClient] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global algorand_client

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    algorand_client = AlgorandClient()
    yield

    await engine.dispose()


app = FastAPI(
    title="ConsentChain API",
    description="DPDP Act Compliant Consent Management on Algorand",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()


async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session


async def verify_fiduciary_api_key(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: AsyncSession = Depends(get_session),
) -> dict:
    api_key = credentials.credentials
    api_key_hash = CryptoUtils.hash_api_key(api_key)

    from sqlalchemy import select
    from api.database import DataFiduciaryDB

    result = await session.execute(
        select(DataFiduciaryDB).where(DataFiduciaryDB.api_key_hash == api_key_hash)
    )
    fiduciary = result.scalar_one_or_none()

    if not fiduciary:
        raise HTTPException(status_code=401, detail="Invalid API key")

    return {
        "fiduciary_id": str(fiduciary.id),
        "name": fiduciary.name,
        "wallet_address": fiduciary.wallet_address,
    }


async def verify_user_jwt(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    import jwt

    token = credentials.credentials
    jwt_secret = os.getenv("JWT_SECRET", "default-secret")

    try:
        payload = jwt.decode(token, jwt_secret, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


@app.get("/")
async def root():
    return {
        "name": "ConsentChain API",
        "version": "1.0.0",
        "description": "DPDP Act Compliant Consent Management",
        "network": os.getenv("ALGORAND_NETWORK", "testnet"),
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


@app.post("/api/v1/fiduciary/register", response_model=APIResponse)
async def register_fiduciary(
    request: FiduciaryRegisterRequest,
    session: AsyncSession = Depends(get_session),
):
    try:
        consent_service = ConsentService(
            session,
            algorand_client,
            CONSENT_APP_ID,
            AUDIT_APP_ID,
        )

        fiduciary, api_key = await consent_service.register_fiduciary(
            name=request.name,
            registration_number=request.registration_number,
            wallet_address=os.getenv("MASTER_ADDRESS", ""),
            contact_email=request.contact_email,
            data_categories=request.data_categories,
            purposes=request.purposes,
        )

        return APIResponse(
            success=True,
            message="Fiduciary registered successfully",
            data={
                "fiduciary_id": str(fiduciary.id),
                "api_key": api_key,
                "note": "Store the API key securely. It will not be shown again.",
            },
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/v1/consent/create", response_model=APIResponse)
async def create_consent(
    request: ConsentCreateRequest,
    fiduciary: dict = Depends(verify_fiduciary_api_key),
    session: AsyncSession = Depends(get_session),
):
    try:
        consent_service = ConsentService(
            session,
            algorand_client,
            CONSENT_APP_ID,
            AUDIT_APP_ID,
        )

        consent = await consent_service.create_consent(
            principal_wallet=request.principal_wallet,
            fiduciary_id=UUID(request.fiduciary_id),
            purpose=request.purpose,
            data_types=request.data_types,
            duration_days=request.duration_days,
            metadata=request.metadata,
            signature=request.signature,
        )

        return APIResponse(
            success=True,
            message="Consent created successfully",
            data={
                "consent_id": str(consent.id),
                "status": consent.status.value,
                "granted_at": consent.granted_at.isoformat(),
                "expires_at": consent.expires_at.isoformat() if consent.expires_at else None,
                "on_chain_tx_id": consent.on_chain_tx_id,
                "consent_hash": consent.consent_hash,
            },
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/v1/consent/batch", response_model=APIResponse)
async def batch_create_consents(
    request: BatchConsentCreateRequest,
    fiduciary: dict = Depends(verify_fiduciary_api_key),
    session: AsyncSession = Depends(get_session),
):
    try:
        consent_service = ConsentService(
            session,
            algorand_client,
            CONSENT_APP_ID,
            AUDIT_APP_ID,
        )

        results = []
        for consent_req in request.consents:
            try:
                consent = await consent_service.create_consent(
                    principal_wallet=consent_req.principal_wallet,
                    fiduciary_id=UUID(consent_req.fiduciary_id),
                    purpose=consent_req.purpose,
                    data_types=consent_req.data_types,
                    duration_days=consent_req.duration_days,
                    metadata=consent_req.metadata,
                    signature=consent_req.signature,
                )
                results.append(
                    {
                        "principal_wallet": consent_req.principal_wallet,
                        "consent_id": str(consent.id),
                        "success": True,
                    }
                )
            except Exception as e:
                results.append(
                    {
                        "principal_wallet": consent_req.principal_wallet,
                        "error": str(e),
                        "success": False,
                    }
                )

        successful = sum(1 for r in results if r["success"])

        return APIResponse(
            success=True,
            message=f"Batch processed: {successful}/{len(results)} consents created",
            data={"results": results, "batch_id": request.batch_id},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/consent/revoke", response_model=APIResponse)
async def revoke_consent(
    request: ConsentRevokeRequest,
    user: dict = Depends(verify_user_jwt),
    session: AsyncSession = Depends(get_session),
):
    try:
        consent_service = ConsentService(
            session,
            algorand_client,
            CONSENT_APP_ID,
            AUDIT_APP_ID,
        )

        consent = await consent_service.revoke_consent(
            consent_id=UUID(request.consent_id),
            reason=request.reason,
            signature=request.signature,
        )

        return APIResponse(
            success=True,
            message="Consent revoked successfully",
            data={
                "consent_id": str(consent.id),
                "status": consent.status.value,
                "revoked_at": consent.revoked_at.isoformat(),
            },
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/v1/consent/modify", response_model=APIResponse)
async def modify_consent(
    request: ConsentModifyRequest,
    user: dict = Depends(verify_user_jwt),
    session: AsyncSession = Depends(get_session),
):
    try:
        consent_service = ConsentService(
            session,
            algorand_client,
            CONSENT_APP_ID,
            AUDIT_APP_ID,
        )

        consent = await consent_service.modify_consent(
            consent_id=UUID(request.consent_id),
            new_purpose=request.new_purpose,
            new_data_types=request.new_data_types,
            new_duration_days=request.new_duration_days,
            reason=request.reason,
            signature=request.signature,
        )

        return APIResponse(
            success=True,
            message="Consent modified successfully",
            data={
                "consent_id": str(consent.id),
                "status": consent.status.value,
                "updated_at": consent.updated_at.isoformat(),
            },
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/v1/consent/verify", response_model=APIResponse)
async def verify_consent(
    request: ConsentVerifyRequest,
    fiduciary: dict = Depends(verify_fiduciary_api_key),
    session: AsyncSession = Depends(get_session),
):
    try:
        consent_service = ConsentService(
            session,
            algorand_client,
            CONSENT_APP_ID,
            AUDIT_APP_ID,
        )

        result = await consent_service.verify_consent(
            consent_id=UUID(request.consent_id),
            verifier_wallet=request.principal_id,
        )

        return APIResponse(
            success=result["valid"],
            message="Consent verified"
            if result["valid"]
            else result.get("reason", "Invalid consent"),
            data=result,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/v1/consent/query", response_model=APIResponse)
async def query_consents(
    principal_id: Optional[str] = None,
    fiduciary_id: Optional[str] = None,
    status: Optional[str] = None,
    purpose: Optional[str] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    page: int = 1,
    limit: int = 20,
    session: AsyncSession = Depends(get_session),
):
    consent_service = ConsentService(
        session,
        algorand_client,
        CONSENT_APP_ID,
        AUDIT_APP_ID,
    )

    consents = await consent_service.query_consents(
        principal_id=UUID(principal_id) if principal_id else None,
        fiduciary_id=UUID(fiduciary_id) if fiduciary_id else None,
        status=status,
        purpose=purpose,
        from_date=from_date,
        to_date=to_date,
        page=page,
        limit=limit,
    )

    return APIResponse(
        success=True,
        message=f"Found {len(consents)} consents",
        data={
            "consents": [
                {
                    "consent_id": str(c.id),
                    "principal_id": str(c.principal_id),
                    "fiduciary_id": str(c.fiduciary_id),
                    "purpose": c.purpose,
                    "data_types": json.loads(c.data_types),
                    "status": c.status.value,
                    "granted_at": c.granted_at.isoformat() if c.granted_at else None,
                    "expires_at": c.expires_at.isoformat() if c.expires_at else None,
                    "consent_hash": c.consent_hash,
                }
                for c in consents
            ],
            "page": page,
            "limit": limit,
        },
    )


@app.get("/api/v1/consent/{consent_id}/history", response_model=APIResponse)
async def get_consent_history(
    consent_id: str,
    user: dict = Depends(verify_user_jwt),
    session: AsyncSession = Depends(get_session),
):
    consent_service = ConsentService(
        session,
        algorand_client,
        CONSENT_APP_ID,
        AUDIT_APP_ID,
    )

    events = await consent_service.get_consent_history(UUID(consent_id))

    return APIResponse(
        success=True,
        message=f"Found {len(events)} events",
        data={
            "events": [
                {
                    "event_id": str(e.id),
                    "event_type": e.event_type.value,
                    "actor": e.actor,
                    "actor_type": e.actor_type,
                    "previous_status": e.previous_status.value if e.previous_status else None,
                    "new_status": e.new_status.value,
                    "tx_id": e.tx_id,
                    "created_at": e.created_at.isoformat(),
                }
                for e in events
            ],
        },
    )


@app.post("/api/v1/audit/query", response_model=APIResponse)
async def query_audit_logs(
    request: AuditQueryRequest,
    fiduciary: dict = Depends(verify_fiduciary_api_key),
    session: AsyncSession = Depends(get_session),
):
    audit_service = AuditService(
        session, algorand_client and AuditTrailClient(algorand_client, AUDIT_APP_ID)
    )

    logs = await audit_service.get_audit_trail(
        principal_id=UUID(request.principal_id) if request.principal_id else None,
        fiduciary_id=UUID(request.fiduciary_id) if request.fiduciary_id else None,
        consent_id=UUID(request.consent_id) if request.consent_id else None,
        event_type=request.event_type,
        from_date=request.from_date,
        to_date=request.to_date,
        page=request.page,
        limit=request.limit,
    )

    return APIResponse(
        success=True,
        message=f"Found {len(logs)} audit logs",
        data={
            "logs": [
                {
                    "log_id": str(l.id),
                    "action": l.action,
                    "resource_type": l.resource_type,
                    "resource_id": str(l.resource_id),
                    "on_chain_reference": l.on_chain_reference,
                    "created_at": l.created_at.isoformat(),
                }
                for l in logs
            ],
        },
    )


@app.post("/api/v1/audit/merkle-root", response_model=APIResponse)
async def generate_merkle_root(
    event_ids: List[str],
    fiduciary: dict = Depends(verify_fiduciary_api_key),
    session: AsyncSession = Depends(get_session),
):
    audit_service = AuditService(
        session, algorand_client and AuditTrailClient(algorand_client, AUDIT_APP_ID)
    )

    merkle_root, tx_id = await audit_service.generate_merkle_root([UUID(eid) for eid in event_ids])

    return APIResponse(
        success=True,
        message="Merkle root generated and anchored on-chain",
        data={
            "merkle_root": merkle_root,
            "tx_id": tx_id,
        },
    )


@app.post("/api/v1/compliance/report", response_model=APIResponse)
async def generate_compliance_report(
    request: ComplianceReportRequest,
    fiduciary: dict = Depends(verify_fiduciary_api_key),
    session: AsyncSession = Depends(get_session),
):
    compliance_service = ComplianceService(session)

    report = await compliance_service.generate_compliance_report(
        fiduciary_id=UUID(request.fiduciary_id),
        period_start=request.period_start,
        period_end=request.period_end,
    )

    return APIResponse(
        success=True,
        message="Compliance report generated",
        data={
            "report_id": str(report.id),
            "fiduciary_id": str(report.fiduciary_id),
            "period_start": report.period_start.isoformat(),
            "period_end": report.period_end.isoformat(),
            "total_consents": report.total_consents,
            "active_consents": report.active_consents,
            "revoked_consents": report.revoked_consents,
            "expired_consents": report.expired_consents,
            "compliance_score": report.compliance_score,
            "on_chain_hash": report.on_chain_hash,
        },
    )


@app.get("/api/v1/compliance/status/{fiduciary_id}", response_model=APIResponse)
async def get_compliance_status(
    fiduciary_id: str,
    fiduciary: dict = Depends(verify_fiduciary_api_key),
    session: AsyncSession = Depends(get_session),
):
    compliance_service = ComplianceService(session)

    status = await compliance_service.get_fiduciary_compliance_status(UUID(fiduciary_id))

    return APIResponse(
        success=True,
        message="Compliance status retrieved",
        data=status,
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
