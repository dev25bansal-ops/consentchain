"""Public routes - User-facing endpoints with rate limiting."""

import json
import os
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas import APIResponse
from api.services import ConsentService
from api.database import DataPrincipalDB, DataFiduciaryDB, ConsentRecordDB, ConsentStatusDB
from api.dependencies import get_session
from core.crypto import CryptoUtils
from api.middleware.rate_limiting import limiter

router = APIRouter(prefix="/api/v1/public", tags=["public"])
TESTING = os.getenv("TESTING", "").lower() in ("1", "true", "yes")


class UserConsentCreateRequest(BaseModel):
    fiduciary_id: str
    purpose: str
    data_types: list[str]
    duration_days: int
    principal_wallet: str
    signature: str
    metadata: Optional[dict] = None


class UserGrievanceRequest(BaseModel):
    fiduciary_id: str
    principal_wallet: str
    grievance_type: str
    subject: str = Field(..., min_length=10, max_length=255)
    description: str = Field(..., min_length=50)
    consent_id: Optional[str] = None


@router.get("/consent/{principal_wallet}", response_model=APIResponse)
@limiter.limit("10/minute")
async def list_user_consents(
    request: Request,
    principal_wallet: str,
    status: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(DataPrincipalDB).where(DataPrincipalDB.wallet_address == principal_wallet)
    )
    principal = result.scalar_one_or_none()

    if not principal:
        return APIResponse(
            success=True,
            message="No consents found",
            data={"consents": [], "page": page, "limit": limit, "total": 0},
        )

    query = select(ConsentRecordDB).where(ConsentRecordDB.principal_id == principal.id)

    if status:
        try:
            query = query.where(ConsentRecordDB.status == ConsentStatusDB(status))
        except ValueError:
            pass

    query = (
        query.order_by(ConsentRecordDB.created_at.desc()).offset((page - 1) * limit).limit(limit)
    )

    result = await session.execute(query)
    consents = result.scalars().all()

    count_query = select(ConsentRecordDB).where(ConsentRecordDB.principal_id == principal.id)
    if status:
        try:
            count_query = count_query.where(ConsentRecordDB.status == ConsentStatusDB(status))
        except ValueError:
            pass
    count_result = await session.execute(count_query)
    total = len(count_result.scalars().all())

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
            "total": total,
        },
    )


@router.get("/fiduciaries", response_model=APIResponse)
@limiter.limit("10/minute")
async def list_public_fiduciaries(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(DataFiduciaryDB).where(DataFiduciaryDB.compliance_status == "ACTIVE")
    )
    fiduciaries = result.scalars().all()

    return APIResponse(
        success=True,
        message="Active fiduciaries retrieved",
        data={
            "fiduciaries": [
                {
                    "id": str(f.id),
                    "name": f.name,
                    "registration_number": f.registration_number,
                    "data_categories": json.loads(f.data_categories) if f.data_categories else [],
                    "purposes": json.loads(f.purposes) if f.purposes else [],
                }
                for f in fiduciaries
            ]
        },
    )


@router.post("/consent/create", response_model=APIResponse)
@limiter.limit("10/minute")
async def user_create_consent(
    request: Request,
    body: UserConsentCreateRequest,
    session: AsyncSession = Depends(get_session),
):
    from api.main import algorand_client, CONSENT_APP_ID, AUDIT_APP_ID

    try:
        consent_service = ConsentService(
            session,
            algorand_client,
            CONSENT_APP_ID,
            AUDIT_APP_ID,
        )

        consent = await consent_service.create_consent(
            principal_wallet=body.principal_wallet,
            fiduciary_id=UUID(body.fiduciary_id),
            purpose=body.purpose,
            data_types=body.data_types,
            duration_days=body.duration_days,
            metadata=body.metadata,
            signature=body.signature,
            skip_signature_verification=TESTING,
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


@router.post("/grievance/submit", response_model=APIResponse)
@limiter.limit("5/minute")
async def public_submit_grievance(
    request: Request,
    body: UserGrievanceRequest,
    session: AsyncSession = Depends(get_session),
):
    from api.grievance import GrievanceService, GrievanceCreate, GrievanceType

    result = await session.execute(
        select(DataPrincipalDB).where(DataPrincipalDB.wallet_address == body.principal_wallet)
    )
    principal = result.scalar_one_or_none()

    if not principal:
        principal = DataPrincipalDB(
            wallet_address=body.principal_wallet,
            email_hash=CryptoUtils.sha256(f"placeholder_{body.principal_wallet}"),
        )
        session.add(principal)
        await session.flush()

    try:
        grievance_type = GrievanceType(body.grievance_type)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid grievance type")

    service = GrievanceService(session)

    grievance_create = GrievanceCreate(
        principal_id=principal.id,
        fiduciary_id=UUID(body.fiduciary_id),
        grievance_type=grievance_type,
        subject=body.subject,
        description=body.description,
        consent_id=UUID(body.consent_id) if body.consent_id else None,
    )

    grievance = await service.submit_grievance(grievance_create)

    return APIResponse(
        success=True,
        message="Grievance submitted successfully",
        data={
            "grievance_id": str(grievance.id),
            "status": grievance.status.value,
            "created_at": grievance.created_at.isoformat(),
        },
    )


@router.get("/grievance/{principal_wallet}", response_model=APIResponse)
@limiter.limit("10/minute")
async def list_user_grievances(
    request: Request,
    principal_wallet: str,
    session: AsyncSession = Depends(get_session),
):
    from api.grievance import GrievanceService

    result = await session.execute(
        select(DataPrincipalDB).where(DataPrincipalDB.wallet_address == principal_wallet)
    )
    principal = result.scalar_one_or_none()

    if not principal:
        return APIResponse(
            success=True,
            message="No grievances found",
            data={"grievances": []},
        )

    service = GrievanceService(session)
    grievances = await service.list_grievances(principal_id=principal.id)

    return APIResponse(
        success=True,
        message=f"Found {len(grievances)} grievances",
        data={
            "grievances": [
                {
                    "id": str(g.id),
                    "type": g.grievance_type.value,
                    "subject": g.subject,
                    "status": g.status.value,
                    "priority": g.priority.value,
                    "created_at": g.created_at.isoformat(),
                    "resolution": g.resolution,
                    "resolution_date": g.resolution_date.isoformat() if g.resolution_date else None,
                }
                for g in grievances
            ]
        },
    )
