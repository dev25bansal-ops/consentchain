"""Consent routes - Consent lifecycle management."""

import json
import os
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from api.schemas import (
    APIResponse,
    ConsentCreateRequest,
    ConsentRevokeRequest,
    ConsentModifyRequest,
    ConsentVerifyRequest,
)
from api.services import ConsentService
from api.dependencies import (
    get_session,
    verify_fiduciary_api_key,
    verify_user_jwt,
)
from core.models import ConsentRecord, ConsentStatus

router = APIRouter(prefix="/api/v1/consent", tags=["consent"])
TESTING = os.getenv("TESTING", "").lower() in ("1", "true", "yes")

from api.middleware.rate_limiting import limiter


class BatchConsentCreateRequest(BaseModel):
    batch_id: str = Field(..., description="Unique batch identifier")
    consents: list[ConsentCreateRequest]


@router.post("/create", response_model=APIResponse)
@limiter.limit("100/minute")
async def create_consent(
    request: Request,
    body: ConsentCreateRequest,
    fiduciary: dict = Depends(verify_fiduciary_api_key),
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


@router.post("/batch", response_model=APIResponse)
@limiter.limit("10/minute")
async def batch_create_consents(
    request: Request,
    body: BatchConsentCreateRequest,
    fiduciary: dict = Depends(verify_fiduciary_api_key),
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

        results = []
        for consent_req in body.consents:
            try:
                consent = await consent_service.create_consent(
                    principal_wallet=consent_req.principal_wallet,
                    fiduciary_id=UUID(consent_req.fiduciary_id),
                    purpose=consent_req.purpose,
                    data_types=consent_req.data_types,
                    duration_days=consent_req.duration_days,
                    metadata=consent_req.metadata,
                    signature=consent_req.signature,
                    skip_signature_verification=TESTING,
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
            data={"results": results, "batch_id": body.batch_id},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/revoke", response_model=APIResponse)
@limiter.limit("50/minute")
async def revoke_consent(
    request: Request,
    body: ConsentRevokeRequest,
    user: dict = Depends(verify_user_jwt),
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

        consent = await consent_service.revoke_consent(
            consent_id=UUID(body.consent_id),
            reason=body.reason,
            signature=body.signature,
            skip_signature_verification=TESTING,
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


@router.post("/modify", response_model=APIResponse)
async def modify_consent(
    body: ConsentModifyRequest,
    user: dict = Depends(verify_user_jwt),
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

        consent = await consent_service.modify_consent(
            consent_id=UUID(body.consent_id),
            new_purpose=body.new_purpose,
            new_data_types=body.new_data_types,
            new_duration_days=body.new_duration_days,
            reason=body.reason,
            signature=body.signature,
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


@router.post("/verify", response_model=APIResponse)
@limiter.limit("1000/minute")
async def verify_consent(
    request: Request,
    body: ConsentVerifyRequest,
    fiduciary: dict = Depends(verify_fiduciary_api_key),
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

        result = await consent_service.verify_consent(
            consent_id=UUID(body.consent_id),
            verifier_wallet=body.principal_id,
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


@router.get("/query", response_model=APIResponse)
@limiter.limit("500/minute")
async def query_consents(
    request: Request,
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
    from api.main import algorand_client, CONSENT_APP_ID, AUDIT_APP_ID

    consent_service = ConsentService(
        session,
        algorand_client,
        CONSENT_APP_ID,
        AUDIT_APP_ID,
    )

    result = await consent_service.query_consents(
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
        message=f"Found {result['total']} consents",
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
                for c in result["items"]
            ],
            "page": result["page"],
            "limit": result["limit"],
            "total": result["total"],
            "pages": result["pages"],
        },
    )


@router.get("/{consent_id}", response_model=APIResponse)
async def get_consent_by_id(
    consent_id: str,
    user: dict = Depends(verify_user_jwt),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(ConsentRecord).where(ConsentRecord.id == UUID(consent_id))
    )
    consent = result.scalar_one_or_none()

    if not consent:
        raise HTTPException(status_code=404, detail="Consent not found")

    return APIResponse(
        success=True,
        message="Consent retrieved",
        data={
            "consent_id": str(consent.id),
            "principal_id": str(consent.principal_id),
            "fiduciary_id": str(consent.fiduciary_id),
            "purpose": consent.purpose,
            "data_types": json.loads(consent.data_types),
            "status": consent.status.value,
            "granted_at": consent.granted_at.isoformat() if consent.granted_at else None,
            "expires_at": consent.expires_at.isoformat() if consent.expires_at else None,
            "revoked_at": consent.revoked_at.isoformat() if consent.revoked_at else None,
            "consent_hash": consent.consent_hash,
            "on_chain_tx_id": consent.on_chain_tx_id,
        },
    )


@router.get("/{consent_id}/history", response_model=APIResponse)
async def get_consent_history(
    consent_id: str,
    user: dict = Depends(verify_user_jwt),
    session: AsyncSession = Depends(get_session),
):
    from api.main import algorand_client, CONSENT_APP_ID, AUDIT_APP_ID

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
