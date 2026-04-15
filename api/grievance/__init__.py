"""Grievance Management System - DPDP Act Section 13 Compliance."""

from datetime import datetime, timezone, timedelta
from typing import Optional, List
from uuid import UUID, uuid4
from enum import Enum
from dataclasses import dataclass

from pydantic import BaseModel, Field
from sqlalchemy import select, and_, Index
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from api.database import Base


class GrievanceType(str, Enum):
    ACCESS = "ACCESS"
    CORRECTION = "CORRECTION"
    DELETION = "DELETION"
    OBJECTION = "OBJECTION"
    PORTABILITY = "PORTABILITY"
    UNLAWFUL_PROCESSING = "UNLAWFUL_PROCESSING"
    BREACH_NOTIFICATION = "BREACH_NOTIFICATION"
    OTHER = "OTHER"


class GrievanceStatus(str, Enum):
    SUBMITTED = "SUBMITTED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    IN_PROGRESS = "IN_PROGRESS"
    AWAITING_INFO = "AWAITING_INFO"
    RESOLVED = "RESOLVED"
    REJECTED = "REJECTED"
    ESCALATED = "ESCALATED"


class GrievancePriority(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    URGENT = "URGENT"


class GrievanceDB(Base):
    __tablename__ = "grievances"
    __table_args__ = (
        Index("ix_grievance_fiduciary_status_created", "fiduciary_id", "status", "created_at"),
        Index("ix_grievance_principal_status", "principal_id", "status"),
        {"extend_existing": True},
    )

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    principal_id = Column(
        PG_UUID(as_uuid=True), ForeignKey("data_principals.id"), nullable=False, index=True
    )
    fiduciary_id = Column(
        PG_UUID(as_uuid=True), ForeignKey("data_fiduciaries.id"), nullable=False, index=True
    )

    grievance_type = Column(SQLEnum(GrievanceType), nullable=False)
    status = Column(SQLEnum(GrievanceStatus), default=GrievanceStatus.SUBMITTED, index=True)
    priority = Column(SQLEnum(GrievancePriority), default=GrievancePriority.MEDIUM)

    subject = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)

    consent_id = Column(PG_UUID(as_uuid=True), nullable=True)
    related_data = Column(Text, nullable=True)

    resolution = Column(Text, nullable=True)
    resolution_date = Column(DateTime, nullable=True)

    assigned_to = Column(PG_UUID(as_uuid=True), nullable=True)

    acknowledgement_date = Column(DateTime, nullable=True)
    expected_resolution_date = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    communications = relationship("GrievanceCommunicationDB", back_populates="grievance")


class GrievanceCommunicationDB(Base):
    __tablename__ = "grievance_communications"
    __table_args__ = {"extend_existing": True}

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    grievance_id = Column(
        PG_UUID(as_uuid=True), ForeignKey("grievances.id"), nullable=False, index=True
    )

    sender_type = Column(String(50), nullable=False)
    sender_id = Column(PG_UUID(as_uuid=True), nullable=False)

    message = Column(Text, nullable=False)
    attachments = Column(Text, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    grievance = relationship("GrievanceDB", back_populates="communications")


class GrievanceCreate(BaseModel):
    principal_id: UUID
    fiduciary_id: UUID
    grievance_type: GrievanceType
    subject: str = Field(..., min_length=10, max_length=255)
    description: str = Field(..., min_length=50)
    consent_id: Optional[UUID] = None
    related_data: Optional[dict] = None


class GrievanceUpdate(BaseModel):
    status: Optional[GrievanceStatus] = None
    priority: Optional[GrievancePriority] = None
    assigned_to: Optional[UUID] = None
    resolution: Optional[str] = None


class GrievanceCommunication(BaseModel):
    message: str
    attachments: Optional[List[str]] = None


@dataclass
class SLAConfig:
    acknowledgement_hours: int = 24
    resolution_days: int = 30
    urgent_resolution_days: int = 7


class GrievanceService:
    def __init__(self, db: AsyncSession, sla_config: Optional[SLAConfig] = None):
        self.db = db
        self.sla_config = sla_config or SLAConfig()

    async def _log_audit(
        self,
        principal_id: Optional[UUID],
        fiduciary_id: Optional[UUID],
        action: str,
        resource_type: str,
        resource_id: UUID,
    ) -> None:
        from api.database import AuditLogDB

        audit = AuditLogDB(
            principal_id=principal_id,
            fiduciary_id=fiduciary_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            created_at=datetime.now(timezone.utc),
        )
        self.db.add(audit)

    async def submit_grievance(self, data: GrievanceCreate) -> GrievanceDB:
        grievance = GrievanceDB(
            id=uuid4(),
            principal_id=data.principal_id,
            fiduciary_id=data.fiduciary_id,
            grievance_type=data.grievance_type,
            status=GrievanceStatus.SUBMITTED,
            subject=data.subject,
            description=data.description,
            consent_id=data.consent_id,
            created_at=datetime.now(timezone.utc),
        )

        if data.grievance_type == GrievanceType.BREACH_NOTIFICATION:
            grievance.priority = GrievancePriority.URGENT

        self.db.add(grievance)
        await self._log_audit(
            principal_id=data.principal_id,
            fiduciary_id=data.fiduciary_id,
            action="GRIEVANCE_SUBMITTED",
            resource_type="grievance",
            resource_id=grievance.id,
        )
        await self.db.commit()
        await self.db.refresh(grievance)

        return grievance

    async def acknowledge_grievance(self, grievance_id: UUID) -> GrievanceDB:
        result = await self.db.execute(select(GrievanceDB).where(GrievanceDB.id == grievance_id))
        grievance = result.scalar_one_or_none()

        if not grievance:
            raise ValueError(f"Grievance {grievance_id} not found")

        grievance.status = GrievanceStatus.ACKNOWLEDGED
        grievance.acknowledgement_date = datetime.now(timezone.utc)
        grievance.expected_resolution_date = datetime.now(timezone.utc) + timedelta(
            days=self.sla_config.resolution_days
        )

        await self._log_audit(
            principal_id=grievance.principal_id,
            fiduciary_id=grievance.fiduciary_id,
            action="GRIEVANCE_ACKNOWLEDGED",
            resource_type="grievance",
            resource_id=grievance_id,
        )
        await self.db.commit()
        await self.db.refresh(grievance)

        return grievance

    async def resolve_grievance(
        self,
        grievance_id: UUID,
        resolution: str,
    ) -> GrievanceDB:
        result = await self.db.execute(select(GrievanceDB).where(GrievanceDB.id == grievance_id))
        grievance = result.scalar_one_or_none()

        if not grievance:
            raise ValueError(f"Grievance {grievance_id} not found")

        grievance.status = GrievanceStatus.RESOLVED
        grievance.resolution = resolution
        grievance.resolution_date = datetime.now(timezone.utc)

        await self._log_audit(
            principal_id=grievance.principal_id,
            fiduciary_id=grievance.fiduciary_id,
            action="GRIEVANCE_RESOLVED",
            resource_type="grievance",
            resource_id=grievance_id,
        )
        await self.db.commit()
        await self.db.refresh(grievance)

        return grievance

    async def escalate_grievance(
        self,
        grievance_id: UUID,
        reason: str,
    ) -> GrievanceDB:
        result = await self.db.execute(select(GrievanceDB).where(GrievanceDB.id == grievance_id))
        grievance = result.scalar_one_or_none()

        if not grievance:
            raise ValueError(f"Grievance {grievance_id} not found")

        grievance.status = GrievanceStatus.ESCALATED

        await self._add_communication(
            grievance_id,
            "SYSTEM",
            uuid4(),
            f"Grievance escalated: {reason}",
        )

        await self.db.commit()
        await self.db.refresh(grievance)

        return grievance

    async def add_communication(
        self,
        grievance_id: UUID,
        sender_type: str,
        sender_id: UUID,
        message: str,
        attachments: Optional[List[str]] = None,
    ) -> GrievanceCommunicationDB:
        return await self._add_communication(
            grievance_id, sender_type, sender_id, message, attachments
        )

    async def _add_communication(
        self,
        grievance_id: UUID,
        sender_type: str,
        sender_id: UUID,
        message: str,
        attachments: Optional[List[str]] = None,
    ) -> GrievanceCommunicationDB:
        import json

        comm = GrievanceCommunicationDB(
            id=uuid4(),
            grievance_id=grievance_id,
            sender_type=sender_type,
            sender_id=sender_id,
            message=message,
            attachments=json.dumps(attachments) if attachments else None,
        )

        self.db.add(comm)
        await self.db.commit()
        await self.db.refresh(comm)

        return comm

    async def list_grievances(
        self,
        fiduciary_id: Optional[UUID] = None,
        principal_id: Optional[UUID] = None,
        status: Optional[GrievanceStatus] = None,
        limit: int = 50,
    ) -> List[GrievanceDB]:
        query = select(GrievanceDB)

        if fiduciary_id:
            query = query.where(GrievanceDB.fiduciary_id == fiduciary_id)
        if principal_id:
            query = query.where(GrievanceDB.principal_id == principal_id)
        if status:
            query = query.where(GrievanceDB.status == status)

        query = query.order_by(GrievanceDB.created_at.desc()).limit(limit)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def check_sla_compliance(self, fiduciary_id: UUID) -> dict:
        result = await self.db.execute(
            select(GrievanceDB).where(
                and_(
                    GrievanceDB.fiduciary_id == fiduciary_id,
                    GrievanceDB.status.in_(
                        [
                            GrievanceStatus.SUBMITTED,
                            GrievanceStatus.ACKNOWLEDGED,
                            GrievanceStatus.IN_PROGRESS,
                        ]
                    ),
                )
            )
        )
        open_grievances = result.scalars().all()

        sla_breaches = []
        for g in open_grievances:
            if g.expected_resolution_date and datetime.now(timezone.utc) > g.expected_resolution_date:
                sla_breaches.append(
                    {
                        "grievance_id": str(g.id),
                        "expected_date": g.expected_resolution_date.isoformat(),
                        "days_overdue": (datetime.now(timezone.utc) - g.expected_resolution_date).days,
                    }
                )

        return {
            "fiduciary_id": str(fiduciary_id),
            "open_grievances": len(open_grievances),
            "sla_breaches": len(sla_breaches),
            "breach_details": sla_breaches,
            "sla_compliance_rate": (
                (len(open_grievances) - len(sla_breaches)) / len(open_grievances) * 100
                if open_grievances
                else 100.0
            ),
        }
