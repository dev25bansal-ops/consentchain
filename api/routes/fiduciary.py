"""Fiduciary routes - Data fiduciary registration and management."""

import os
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas import APIResponse, FiduciaryRegisterRequest
from api.services import ConsentService
from api.dependencies import get_session
from api.middleware.rate_limiting import limiter

router = APIRouter(prefix="/api/v1/fiduciary", tags=["fiduciary"])


@router.post("/register", response_model=APIResponse)
@limiter.limit("5/hour")
async def register_fiduciary(
    request: Request,
    body: FiduciaryRegisterRequest,
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

        fiduciary, api_key = await consent_service.register_fiduciary(
            name=body.name,
            registration_number=body.registration_number,
            wallet_address=os.getenv("MASTER_ADDRESS", ""),
            contact_email=body.contact_email,
            data_categories=body.data_categories,
            purposes=body.purposes,
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
