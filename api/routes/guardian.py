"""Guardian routes - Nominated representative / guardian for vulnerable users."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas import APIResponse
from api.guardian import GuardianService, GuardianRegistration
from api.dependencies import get_session, verify_fiduciary_api_key
from api.middleware.rate_limiting import limiter

router = APIRouter(prefix="/api/v1/guardian", tags=["guardian"])


@router.post("/register", response_model=APIResponse)
@limiter.limit("10/minute")
async def register_guardian(
    http_request: Request,
    registration: GuardianRegistration,
    session: AsyncSession = Depends(get_session),
):
    service = GuardianService(session)
    guardian = await service.register_guardian(registration)

    return APIResponse(
        success=True,
        message="Guardian registered successfully",
        data={
            "guardian_id": str(guardian.id),
            "status": guardian.status.value,
            "principal_id": str(guardian.principal_id),
        },
    )


@router.post("/{guardian_id}/verify", response_model=APIResponse)
async def verify_guardian(
    guardian_id: str,
    fiduciary: dict = Depends(verify_fiduciary_api_key),
    session: AsyncSession = Depends(get_session),
):
    service = GuardianService(session)
    guardian = await service.verify_guardian(UUID(guardian_id), UUID(fiduciary["fiduciary_id"]))

    return APIResponse(
        success=True,
        message="Guardian verified",
        data={
            "guardian_id": str(guardian.id),
            "status": guardian.status.value,
            "verification_date": guardian.verification_date.isoformat()
            if guardian.verification_date
            else None,
        },
    )


@router.get("/check", response_model=APIResponse)
@limiter.limit("100/minute")
async def check_guardian_authorization(
    request: Request,
    guardian_wallet: str,
    principal_id: str,
    action: str,
    session: AsyncSession = Depends(get_session),
):
    service = GuardianService(session)
    authorized = await service.can_guardian_act(
        guardian_wallet,
        UUID(principal_id),
        action,
    )

    return APIResponse(
        success=True,
        message="Guardian authorization checked",
        data={"authorized": authorized},
    )
