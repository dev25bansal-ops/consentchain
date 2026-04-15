"""Deletion routes - Data deletion request and processing."""

import json
import os
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas import APIResponse
from api.deletion import DataDeletionOrchestrator, DeletionRequestCreate, DeletionScope
from api.dependencies import get_session, verify_fiduciary_api_key
from api.middleware.rate_limiting import limiter

router = APIRouter(prefix="/api/v1/deletion", tags=["deletion"])


class DeletionVerifyRequest(BaseModel):
    verification_code: str


@router.post("/request", response_model=APIResponse)
@limiter.limit("10/minute")
async def create_deletion_request(
    request: Request,
    body: DeletionRequestCreate,
    session: AsyncSession = Depends(get_session),
):
    orchestrator = DataDeletionOrchestrator(session)
    deletion_request = await orchestrator.create_deletion_request(body)

    return APIResponse(
        success=True,
        message="Deletion request created",
        data={
            "request_id": str(deletion_request.id),
            "status": deletion_request.status.value,
            "verification_code": deletion_request.verification_code,
            "note": "Please verify this request using the verification code within 24 hours",
        },
    )


@router.post("/{request_id}/verify", response_model=APIResponse)
@limiter.limit("5/minute")
async def verify_deletion_request(
    request: Request,
    request_id: str,
    body: DeletionVerifyRequest,
    session: AsyncSession = Depends(get_session),
):
    orchestrator = DataDeletionOrchestrator(session)
    verified = await orchestrator.verify_deletion_request(
        UUID(request_id),
        body.verification_code,
    )

    if not verified:
        raise HTTPException(
            status_code=400, detail="Invalid verification code or request already processed"
        )

    return APIResponse(
        success=True,
        message="Deletion request verified",
        data={
            "request_id": request_id,
            "status": "VERIFICATION_IN_PROGRESS",
            "next_step": "Deletion will be scheduled within 24-48 hours",
        },
    )


@router.post("/{request_id}/execute", response_model=APIResponse)
@limiter.limit("5/minute")
async def execute_deletion(
    request: Request,
    request_id: str,
    fiduciary: dict = Depends(verify_fiduciary_api_key),
    session: AsyncSession = Depends(get_session),
):
    orchestrator = DataDeletionOrchestrator(session)
    result = await orchestrator.execute_deletion_full(UUID(request_id))

    return APIResponse(
        success=result["success"],
        message=result["message"],
        data={
            "request_id": request_id,
            "status": result["status"],
            "steps": result["steps"],
            "certificate_id": result.get("certificate_id"),
        },
    )


@router.get("/{request_id}/status", response_model=APIResponse)
@limiter.limit("30/minute")
async def get_deletion_status(
    request: Request,
    request_id: str,
    session: AsyncSession = Depends(get_session),
):
    orchestrator = DataDeletionOrchestrator(session)
    deletion_request = await orchestrator.get_deletion_request(UUID(request_id))

    if not deletion_request:
        raise HTTPException(status_code=404, detail="Deletion request not found")

    return APIResponse(
        success=True,
        message="Deletion status retrieved",
        data={
            "request_id": str(deletion_request.id),
            "status": deletion_request.status.value,
            "requested_at": deletion_request.requested_at.isoformat(),
            "scheduled_at": deletion_request.scheduled_at.isoformat()
            if deletion_request.scheduled_at
            else None,
            "completed_at": deletion_request.completed_at.isoformat()
            if deletion_request.completed_at
            else None,
            "exceptions": [e.value for e in deletion_request.exceptions]
            if deletion_request.exceptions
            else [],
        },
    )


@router.get("/{request_id}/certificate", response_model=APIResponse)
@limiter.limit("30/minute")
async def get_deletion_certificate(
    request: Request,
    request_id: str,
    session: AsyncSession = Depends(get_session),
):
    orchestrator = DataDeletionOrchestrator(session)
    certificate = await orchestrator.get_deletion_certificate(UUID(request_id))

    return APIResponse(
        success=True,
        message="Deletion certificate retrieved",
        data=certificate,
    )


@router.get("/list/{principal_id}", response_model=APIResponse)
@limiter.limit("30/minute")
async def list_deletion_requests(
    request: Request,
    principal_id: str,
    status: Optional[str] = None,
    session: AsyncSession = Depends(get_session),
):
    from sqlalchemy import select
    from api.database import DeletionRequestDB

    query = select(DeletionRequestDB).where(DeletionRequestDB.principal_id == UUID(principal_id))

    if status:
        query = query.where(DeletionRequestDB.status == status)

    result = await session.execute(query.order_by(DeletionRequestDB.created_at.desc()))
    requests = result.scalars().all()

    return APIResponse(
        success=True,
        message=f"Found {len(requests)} deletion requests",
        data={
            "requests": [
                {
                    "id": str(r.id),
                    "fiduciary_id": str(r.fiduciary_id),
                    "scope": r.scope,
                    "status": r.status,
                    "created_at": r.created_at.isoformat(),
                    "completed_at": r.completed_at.isoformat() if r.completed_at else None,
                }
                for r in requests
            ]
        },
    )
