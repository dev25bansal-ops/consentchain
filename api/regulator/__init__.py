"""Regulator Audit Portal API - DPA/CERT-In access endpoints."""

from datetime import datetime, timezone, timedelta
from typing import Optional, List
from uuid import UUID
from dataclasses import dataclass, field
from enum import Enum

from pydantic import BaseModel
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession


class AuditRequestStatus(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    REJECTED = "REJECTED"


class AuditRequestType(str, Enum):
    ROUTINE = "ROUTINE"
    COMPLAINT_BASED = "COMPLAINT_BASED"
    INCIDENT = "INCIDENT"
    ANNUAL = "ANNUAL"


@dataclass
class AuditRequest:
    id: UUID
    request_type: AuditRequestType
    status: AuditRequestStatus
    fiduciary_id: UUID
    requested_by: str
    requested_at: datetime
    scope: List[str]
    period_start: datetime
    period_end: datetime
    description: str
    completed_at: Optional[datetime] = None
    report_url: Optional[str] = None


class AuditRequestCreate(BaseModel):
    request_type: AuditRequestType
    fiduciary_id: UUID
    scope: List[str]
    period_start: datetime
    period_end: datetime
    description: str


class AuditFindings(BaseModel):
    finding_id: UUID
    category: str
    severity: str
    description: str
    recommendation: str
    status: str


class RegulatorAuditService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_audit_request(
        self,
        request_type: AuditRequestType,
        fiduciary_id: UUID,
        scope: List[str],
        period_start: datetime,
        period_end: datetime,
        description: str,
        requested_by: str,
    ) -> AuditRequest:
        from uuid import uuid4

        request = AuditRequest(
            id=uuid4(),
            request_type=request_type,
            status=AuditRequestStatus.PENDING,
            fiduciary_id=fiduciary_id,
            requested_by=requested_by,
            requested_at=datetime.now(timezone.utc),
            scope=scope,
            period_start=period_start,
            period_end=period_end,
            description=description,
        )

        return request

    async def get_fiduciary_audit_trail(
        self,
        fiduciary_id: UUID,
        period_start: datetime,
        period_end: datetime,
    ) -> dict:
        from api.database import ConsentRecordDB, ConsentEventDB, AuditLogDB

        consents_result = await self.db.execute(
            select(ConsentRecordDB).where(
                and_(
                    ConsentRecordDB.fiduciary_id == fiduciary_id,
                    ConsentRecordDB.created_at >= period_start,
                    ConsentRecordDB.created_at <= period_end,
                )
            )
        )
        consents = consents_result.scalars().all()

        events_result = await self.db.execute(
            select(ConsentEventDB)
            .join(ConsentRecordDB)
            .where(
                and_(
                    ConsentRecordDB.fiduciary_id == fiduciary_id,
                    ConsentEventDB.created_at >= period_start,
                    ConsentEventDB.created_at <= period_end,
                )
            )
        )
        events = events_result.scalars().all()

        audit_logs_result = await self.db.execute(
            select(AuditLogDB).where(
                and_(
                    AuditLogDB.fiduciary_id == fiduciary_id,
                    AuditLogDB.created_at >= period_start,
                    AuditLogDB.created_at <= period_end,
                )
            )
        )
        audit_logs = audit_logs_result.scalars().all()

        status_counts = {}
        for consent in consents:
            status = (
                consent.status.value if hasattr(consent.status, "value") else str(consent.status)
            )
            status_counts[status] = status_counts.get(status, 0) + 1

        return {
            "fiduciary_id": str(fiduciary_id),
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "summary": {
                "total_consents": len(consents),
                "total_events": len(events),
                "total_audit_logs": len(audit_logs),
                "consent_status_distribution": status_counts,
            },
            "consents": [
                {
                    "id": str(c.id),
                    "principal_id": str(c.principal_id),
                    "purpose": c.purpose,
                    "status": c.status.value if hasattr(c.status, "value") else str(c.status),
                    "created_at": c.created_at.isoformat(),
                    "on_chain_tx_id": c.on_chain_tx_id,
                }
                for c in consents
            ],
            "events": [
                {
                    "id": str(e.id),
                    "consent_id": str(e.consent_id),
                    "event_type": e.event_type.value
                    if hasattr(e.event_type, "value")
                    else str(e.event_type),
                    "created_at": e.created_at.isoformat(),
                    "tx_id": e.tx_id,
                }
                for e in events
            ],
            "audit_logs": [
                {
                    "id": str(a.id),
                    "action": a.action,
                    "resource_type": a.resource_type,
                    "created_at": a.created_at.isoformat(),
                    "on_chain_reference": a.on_chain_reference,
                }
                for a in audit_logs
            ],
        }

    async def verify_on_chain_integrity(
        self,
        fiduciary_id: UUID,
        period_start: datetime,
        period_end: datetime,
    ) -> dict:
        from api.database import ConsentRecordDB, MerkleRootDB

        consents_result = await self.db.execute(
            select(ConsentRecordDB).where(
                and_(
                    ConsentRecordDB.fiduciary_id == fiduciary_id,
                    ConsentRecordDB.created_at >= period_start,
                    ConsentRecordDB.created_at <= period_end,
                    ConsentRecordDB.on_chain_tx_id.isnot(None),
                )
            )
        )
        consents = consents_result.scalars().all()

        on_chain_consents = [c for c in consents if c.on_chain_tx_id]
        pending_consents = [c for c in consents if not c.on_chain_tx_id]

        merkle_roots_result = await self.db.execute(
            select(MerkleRootDB).where(
                and_(
                    MerkleRootDB.created_at >= period_start,
                    MerkleRootDB.created_at <= period_end,
                )
            )
        )
        merkle_roots = merkle_roots_result.scalars().all()

        return {
            "verification_status": "VERIFIED" if len(pending_consents) == 0 else "PARTIAL",
            "on_chain_count": len(on_chain_consents),
            "pending_count": len(pending_consents),
            "merkle_roots": [
                {
                    "root_hash": mr.root_hash,
                    "event_count": mr.event_count,
                    "on_chain_tx_id": mr.on_chain_tx_id,
                }
                for mr in merkle_roots
            ],
            "verified_at": datetime.now(timezone.utc).isoformat(),
        }

    async def generate_regulator_report(
        self,
        fiduciary_id: UUID,
        period_start: datetime,
        period_end: datetime,
    ) -> dict:
        audit_trail = await self.get_fiduciary_audit_trail(fiduciary_id, period_start, period_end)

        integrity_check = await self.verify_on_chain_integrity(
            fiduciary_id, period_start, period_end
        )

        return {
            "report_type": "REGULATOR_AUDIT",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "fiduciary_id": str(fiduciary_id),
            "period": {
                "start": period_start.isoformat(),
                "end": period_end.isoformat(),
            },
            "audit_trail": audit_trail,
            "blockchain_integrity": integrity_check,
            "compliance_indicators": {
                "consent_rate": (
                    audit_trail["summary"]["consent_status_distribution"].get("GRANTED", 0)
                    / max(audit_trail["summary"]["total_consents"], 1)
                ),
                "on_chain_compliance": (
                    integrity_check["on_chain_count"]
                    / max(integrity_check["on_chain_count"] + integrity_check["pending_count"], 1)
                ),
            },
        }


class RegulatorPortalAPI:
    def __init__(self, audit_service: RegulatorAuditService):
        self.audit_service = audit_service

    async def list_audit_requests(
        self,
        status: Optional[AuditRequestStatus] = None,
        limit: int = 50,
    ) -> List[AuditRequest]:
        pass

    async def get_audit_request(self, request_id: UUID) -> Optional[AuditRequest]:
        pass

    async def submit_audit_findings(
        self,
        request_id: UUID,
        findings: List[AuditFindings],
    ) -> dict:
        pass
