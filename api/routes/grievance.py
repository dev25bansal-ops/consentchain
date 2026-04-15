"""Grievance routes - Grievance management for DPDP Act compliance."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas import APIResponse
from api.grievance import GrievanceService, GrievanceCreate, GrievanceStatus
from api.dependencies import get_session, verify_fiduciary_api_key
from api.middleware.rate_limiting import limiter

router = APIRouter(prefix="/api/v1/grievance", tags=["grievance"])


@router.post("/submit", response_model=APIResponse)
@limiter.limit("20/minute")
async def submit_grievance(
    request: Request,
    grievance_data: GrievanceCreate,
    session: AsyncSession = Depends(get_session),
):
    service = GrievanceService(session)
    grievance = await service.submit_grievance(grievance_data)

    return APIResponse(
        success=True,
        message="Grievance submitted successfully",
        data={
            "grievance_id": str(grievance.id),
            "status": grievance.status.value,
            "created_at": grievance.created_at.isoformat(),
        },
    )


@router.post("/{grievance_id}/acknowledge", response_model=APIResponse)
async def acknowledge_grievance(
    grievance_id: str,
    fiduciary: dict = Depends(verify_fiduciary_api_key),
    session: AsyncSession = Depends(get_session),
):
    service = GrievanceService(session)
    grievance = await service.acknowledge_grievance(UUID(grievance_id))

    return APIResponse(
        success=True,
        message="Grievance acknowledged",
        data={
            "grievance_id": str(grievance.id),
            "status": grievance.status.value,
            "expected_resolution_date": grievance.expected_resolution_date.isoformat()
            if grievance.expected_resolution_date
            else None,
        },
    )


@router.post("/{grievance_id}/resolve", response_model=APIResponse)
async def resolve_grievance(
    grievance_id: str,
    resolution: str,
    fiduciary: dict = Depends(verify_fiduciary_api_key),
    session: AsyncSession = Depends(get_session),
):
    service = GrievanceService(session)
    grievance = await service.resolve_grievance(UUID(grievance_id), resolution)

    return APIResponse(
        success=True,
        message="Grievance resolved",
        data={
            "grievance_id": str(grievance.id),
            "status": grievance.status.value,
            "resolution_date": grievance.resolution_date.isoformat()
            if grievance.resolution_date
            else None,
        },
    )


@router.get("/list", response_model=APIResponse)
@limiter.limit("60/minute")
async def list_grievances(
    request: Request,
    fiduciary_id: Optional[str] = None,
    principal_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    session: AsyncSession = Depends(get_session),
):
    service = GrievanceService(session)
    grievances = await service.list_grievances(
        fiduciary_id=UUID(fiduciary_id) if fiduciary_id else None,
        principal_id=UUID(principal_id) if principal_id else None,
        status=GrievanceStatus(status) if status else None,
        limit=limit,
    )

    return APIResponse(
        success=True,
        message=f"Found {len(grievances)} grievances",
        data={
            "grievances": [
                {
                    "id": str(g.id),
                    "principal_id": str(g.principal_id),
                    "fiduciary_id": str(g.fiduciary_id),
                    "type": g.grievance_type.value,
                    "status": g.status.value,
                    "priority": g.priority.value,
                    "subject": g.subject,
                    "created_at": g.created_at.isoformat(),
                }
                for g in grievances
            ],
        },
    )


@router.get("/sla/{fiduciary_id}", response_model=APIResponse)
async def check_sla_compliance(
    fiduciary_id: str,
    fiduciary: dict = Depends(verify_fiduciary_api_key),
    session: AsyncSession = Depends(get_session),
):
    service = GrievanceService(session)
    sla_status = await service.check_sla_compliance(UUID(fiduciary_id))

    return APIResponse(
        success=True,
        message="SLA compliance checked",
        data=sla_status,
    )
