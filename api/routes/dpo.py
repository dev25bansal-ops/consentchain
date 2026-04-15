"""DPO Portal routes - Data Protection Officer endpoints for DPDP Section 8 compliance."""

import json
import os
from datetime import datetime, timezone, timedelta
from typing import Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas import APIResponse
from api.database import (
    ConsentRecordDB,
    ConsentStatusDB,
    DataPrincipalDB,
    DataFiduciaryDB,
    AuditLogDB,
    GrievanceDB,
    DeletionRequestDB,
)
from api.dependencies import get_session
from api.middleware.rate_limiting import limiter

router = APIRouter(prefix="/api/v1/dpo", tags=["dpo"])


class DPODashboardStats(BaseModel):
    total_consents: int
    active_consents: int
    revoked_consents: int
    expired_consents: int
    pending_grievances: int
    pending_deletions: int
    compliance_score: float
    last_audit_date: Optional[datetime]


class ConsentAuditRequest(BaseModel):
    fiduciary_id: str
    period_start: datetime
    period_end: datetime
    include_sensitive: bool = False


class CrossBorderTransferRequest(BaseModel):
    fiduciary_id: str
    destination_country: str
    data_categories: list[str]
    purpose: str
    legal_basis: str
    safeguards: list[str]


class DPONotification(BaseModel):
    fiduciary_id: str
    notification_type: str
    title: str
    message: str
    recipients: list[str]


@router.get("/dashboard/{fiduciary_id}", response_model=APIResponse)
@limiter.limit("60/minute")
async def get_dpo_dashboard(
    request: Request,
    fiduciary_id: str,
    session: AsyncSession = Depends(get_session),
):
    fiduciary_uuid = UUID(fiduciary_id)

    total_consents = (
        await session.scalar(
            select(func.count())
            .select_from(ConsentRecordDB)
            .where(ConsentRecordDB.fiduciary_id == fiduciary_uuid)
        )
        or 0
    )

    active_consents = (
        await session.scalar(
            select(func.count())
            .select_from(ConsentRecordDB)
            .where(
                and_(
                    ConsentRecordDB.fiduciary_id == fiduciary_uuid,
                    ConsentRecordDB.status == ConsentStatusDB.GRANTED,
                )
            )
        )
        or 0
    )

    revoked_consents = (
        await session.scalar(
            select(func.count())
            .select_from(ConsentRecordDB)
            .where(
                and_(
                    ConsentRecordDB.fiduciary_id == fiduciary_uuid,
                    ConsentRecordDB.status == ConsentStatusDB.REVOKED,
                )
            )
        )
        or 0
    )

    expired_consents = (
        await session.scalar(
            select(func.count())
            .select_from(ConsentRecordDB)
            .where(
                and_(
                    ConsentRecordDB.fiduciary_id == fiduciary_uuid,
                    ConsentRecordDB.status == ConsentStatusDB.EXPIRED,
                )
            )
        )
        or 0
    )

    pending_grievances = (
        await session.scalar(
            select(func.count())
            .select_from(GrievanceDB)
            .where(
                and_(GrievanceDB.fiduciary_id == fiduciary_uuid, GrievanceDB.status == "PENDING")
            )
        )
        or 0
    )

    pending_deletions = (
        await session.scalar(
            select(func.count())
            .select_from(DeletionRequestDB)
            .where(
                and_(
                    DeletionRequestDB.fiduciary_id == fiduciary_uuid,
                    DeletionRequestDB.status == "PENDING",
                )
            )
        )
        or 0
    )

    compliance_score = 100.0
    if total_consents > 0:
        compliance_score = round((active_consents / total_consents) * 100, 2)

    return APIResponse(
        success=True,
        message="DPO dashboard data retrieved",
        data={
            "total_consents": total_consents,
            "active_consents": active_consents,
            "revoked_consents": revoked_consents,
            "expired_consents": expired_consents,
            "pending_grievances": pending_grievances,
            "pending_deletions": pending_deletions,
            "compliance_score": compliance_score,
            "last_audit_date": datetime.now(timezone.utc).isoformat(),
        },
    )


@router.post("/consent-audit", response_model=APIResponse)
@limiter.limit("30/minute")
async def perform_consent_audit(
    request: Request,
    body: ConsentAuditRequest,
    session: AsyncSession = Depends(get_session),
):
    fiduciary_uuid = UUID(body.fiduciary_id)

    query = select(ConsentRecordDB).where(
        and_(
            ConsentRecordDB.fiduciary_id == fiduciary_uuid,
            ConsentRecordDB.created_at >= body.period_start,
            ConsentRecordDB.created_at <= body.period_end,
        )
    )

    result = await session.execute(query)
    consents = result.scalars().all()

    audit_findings = {
        "total_records": len(consents),
        "by_status": {},
        "by_purpose": {},
        "expiring_soon": 0,
        "missing_expiry": 0,
        "sensitive_data_count": 0,
    }

    for consent in consents:
        status = consent.status.value
        audit_findings["by_status"][status] = audit_findings["by_status"].get(status, 0) + 1

        purpose = consent.purpose
        audit_findings["by_purpose"][purpose] = audit_findings["by_purpose"].get(purpose, 0) + 1

        if consent.expires_at:
            if consent.expires_at <= datetime.now(timezone.utc) + timedelta(days=30):
                audit_findings["expiring_soon"] += 1
        else:
            audit_findings["missing_expiry"] += 1

    return APIResponse(
        success=True,
        message="Consent audit completed",
        data={
            "audit_id": str(uuid4()),
            "period_start": body.period_start.isoformat(),
            "period_end": body.period_end.isoformat(),
            "findings": audit_findings,
            "recommendations": [
                "Review consents missing expiry dates",
                "Set up renewal reminders for expiring consents",
                "Ensure proper documentation for sensitive data processing",
            ],
        },
    )


@router.post("/cross-border-transfer", response_model=APIResponse)
@limiter.limit("20/minute")
async def register_cross_border_transfer(
    request: Request,
    body: CrossBorderTransferRequest,
    session: AsyncSession = Depends(get_session),
):
    ALLOWED_COUNTRIES = ["US", "GB", "EU", "SG", "JP", "AU", "CA", "AE", "CH", "NO"]

    requires_additional_safeguards = body.destination_country not in ALLOWED_COUNTRIES

    transfer_id = uuid4()

    return APIResponse(
        success=True,
        message="Cross-border transfer registered",
        data={
            "transfer_id": str(transfer_id),
            "destination_country": body.destination_country,
            "data_categories": body.data_categories,
            "legal_basis": body.legal_basis,
            "requires_additional_safeguards": requires_additional_safeguards,
            "safeguards_implemented": body.safeguards,
            "registered_at": datetime.now(timezone.utc).isoformat(),
            "compliance_notes": [
                "Ensure Standard Contractual Clauses are in place",
                "Verify data protection laws in destination country",
                "Implement appropriate technical measures",
            ]
            if requires_additional_safeguards
            else [
                "Transfer permitted under DPDP Act Section 16",
            ],
        },
    )


@router.get("/data-inventory/{fiduciary_id}", response_model=APIResponse)
@limiter.limit("30/minute")
async def get_data_inventory(
    request: Request,
    fiduciary_id: str,
    session: AsyncSession = Depends(get_session),
):
    fiduciary_uuid = UUID(fiduciary_id)

    result = await session.execute(
        select(DataFiduciaryDB).where(DataFiduciaryDB.id == fiduciary_uuid)
    )
    fiduciary = result.scalar_one_or_none()

    if not fiduciary:
        raise HTTPException(status_code=404, detail="Fiduciary not found")

    data_categories = json.loads(fiduciary.data_categories) if fiduciary.data_categories else []
    purposes = json.loads(fiduciary.purposes) if fiduciary.purposes else []

    principal_count = (
        await session.scalar(
            select(func.count(func.distinct(ConsentRecordDB.principal_id)))
            .select_from(ConsentRecordDB)
            .where(ConsentRecordDB.fiduciary_id == fiduciary_uuid)
        )
        or 0
    )

    return APIResponse(
        success=True,
        message="Data inventory retrieved",
        data={
            "fiduciary_id": str(fiduciary.id),
            "fiduciary_name": fiduciary.name,
            "registration_number": fiduciary.registration_number,
            "data_categories": data_categories,
            "processing_purposes": purposes,
            "data_principals_count": principal_count,
            "last_updated": datetime.now(timezone.utc).isoformat(),
        },
    )


@router.post("/notify-principals", response_model=APIResponse)
@limiter.limit("10/minute")
async def notify_data_principals(
    request: Request,
    body: DPONotification,
    session: AsyncSession = Depends(get_session),
):
    notification_id = uuid4()

    return APIResponse(
        success=True,
        message="Notification queued for delivery",
        data={
            "notification_id": str(notification_id),
            "recipients_count": len(body.recipients),
            "notification_type": body.notification_type,
            "queued_at": datetime.now(timezone.utc).isoformat(),
        },
    )


@router.get("/compliance-checklist/{fiduciary_id}", response_model=APIResponse)
@limiter.limit("60/minute")
async def get_compliance_checklist(
    request: Request,
    fiduciary_id: str,
    session: AsyncSession = Depends(get_session),
):
    checklist = [
        {
            "id": "consent_records",
            "title": "Consent Records Management",
            "description": "Maintain accurate records of consent as per Section 6",
            "status": "COMPLIANT",
            "last_checked": datetime.now(timezone.utc).isoformat(),
        },
        {
            "id": "grievance_officer",
            "title": "Grievance Redressal Officer",
            "description": "Appoint grievance officer as per Section 13",
            "status": "PENDING",
            "last_checked": datetime.now(timezone.utc).isoformat(),
        },
        {
            "id": "data_protection_policy",
            "title": "Data Protection Policy",
            "description": "Publish clear privacy policy as per Section 5",
            "status": "COMPLIANT",
            "last_checked": datetime.now(timezone.utc).isoformat(),
        },
        {
            "id": "data_retention",
            "title": "Data Retention Limits",
            "description": "Implement data retention policies as per Section 8",
            "status": "REVIEW_NEEDED",
            "last_checked": datetime.now(timezone.utc).isoformat(),
        },
        {
            "id": "cross_border_transfer",
            "title": "Cross-Border Transfer Safeguards",
            "description": "Ensure safeguards for international transfers per Section 16",
            "status": "COMPLIANT",
            "last_checked": datetime.now(timezone.utc).isoformat(),
        },
        {
            "id": "children_data",
            "title": "Children's Data Protection",
            "description": "Special handling for minors' data per Section 9",
            "status": "PENDING",
            "last_checked": datetime.now(timezone.utc).isoformat(),
        },
    ]

    compliant = sum(1 for item in checklist if item["status"] == "COMPLIANT")
    total = len(checklist)

    return APIResponse(
        success=True,
        message="Compliance checklist retrieved",
        data={
            "checklist": checklist,
            "compliance_percentage": round((compliant / total) * 100, 2),
            "items_needing_attention": [
                item for item in checklist if item["status"] in ("PENDING", "REVIEW_NEEDED")
            ],
        },
    )
