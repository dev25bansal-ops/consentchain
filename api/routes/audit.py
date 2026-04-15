"""Audit routes - Audit trail and compliance reporting."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas import APIResponse, AuditQueryRequest, ComplianceReportRequest
from api.services import AuditService, ComplianceService
from api.dependencies import get_session, verify_fiduciary_api_key
from api.middleware.rate_limiting import limiter

router = APIRouter(prefix="/api/v1/audit", tags=["audit"])


@router.post("/query", response_model=APIResponse)
@limiter.limit("100/minute")
async def query_audit_logs(
    request: Request,
    body: AuditQueryRequest,
    fiduciary: dict = Depends(verify_fiduciary_api_key),
    session: AsyncSession = Depends(get_session),
):
    from api.main import algorand_client, AUDIT_APP_ID
    from contracts.client import AuditTrailClient

    audit_service = AuditService(
        session, algorand_client and AuditTrailClient(algorand_client, AUDIT_APP_ID)
    )

    logs = await audit_service.get_audit_trail(
        principal_id=UUID(body.principal_id) if body.principal_id else None,
        fiduciary_id=UUID(body.fiduciary_id) if body.fiduciary_id else None,
        consent_id=UUID(body.consent_id) if body.consent_id else None,
        event_type=body.event_type,
        from_date=body.from_date,
        to_date=body.to_date,
        page=body.page,
        limit=body.limit,
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


@router.post("/merkle-root", response_model=APIResponse)
async def generate_merkle_root(
    event_ids: List[str],
    fiduciary: dict = Depends(verify_fiduciary_api_key),
    session: AsyncSession = Depends(get_session),
):
    from api.main import algorand_client, AUDIT_APP_ID
    from contracts.client import AuditTrailClient

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


@router.post("/compliance/report", response_model=APIResponse)
async def generate_compliance_report(
    body: ComplianceReportRequest,
    fiduciary: dict = Depends(verify_fiduciary_api_key),
    session: AsyncSession = Depends(get_session),
):
    compliance_service = ComplianceService(session)

    report = await compliance_service.generate_compliance_report(
        fiduciary_id=UUID(body.fiduciary_id),
        period_start=body.period_start,
        period_end=body.period_end,
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


@router.get("/compliance/status/{fiduciary_id}", response_model=APIResponse)
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
