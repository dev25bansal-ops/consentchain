"""Nominated Representative / Guardian Flow - DPDP Act Section 14.

Implements the provisions for data principals who require assistance
in exercising their rights, including minors and persons with disabilities.
"""

from datetime import datetime, timezone
from typing import Optional, List
from uuid import UUID, uuid4
from enum import Enum
from dataclasses import dataclass

from pydantic import BaseModel, Field, EmailStr
from sqlalchemy import (
    Column,
    String,
    DateTime,
    Text,
    ForeignKey,
    Boolean,
    Enum as SQLEnum,
    select,
    and_,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from api.database import Base


class GuardianType(str, Enum):
    PARENT = "PARENT"
    LEGAL_GUARDIAN = "LEGAL_GUARDIAN"
    COURT_APPOINTED = "COURT_APPOINTED"
    POWER_OF_ATTORNEY = "POWER_OF_ATTORNEY"
    CAREGIVER = "CAREGIVER"


class GuardianStatus(str, Enum):
    PENDING_VERIFICATION = "PENDING_VERIFICATION"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    REVOKED = "REVOKED"
    EXPIRED = "EXPIRED"


class PrincipalCategory(str, Enum):
    MINOR = "MINOR"
    PERSON_WITH_DISABILITY = "PERSON_WITH_DISABILITY"
    INCAPACITATED = "INCAPACITATED"
    OTHER = "OTHER"


class GuardianDB(Base):
    __tablename__ = "guardians"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)

    guardian_wallet = Column(String(58), nullable=False, index=True)
    guardian_name = Column(String(255), nullable=False)
    guardian_email = Column(String(255), nullable=False)
    guardian_phone = Column(String(20), nullable=True)
    guardian_type = Column(SQLEnum(GuardianType), nullable=False)

    principal_id = Column(
        PG_UUID(as_uuid=True), ForeignKey("data_principals.id"), nullable=False, index=True
    )
    principal_category = Column(SQLEnum(PrincipalCategory), nullable=False)

    status = Column(
        SQLEnum(GuardianStatus), default=GuardianStatus.PENDING_VERIFICATION, index=True
    )

    relationship_document = Column(Text, nullable=True)
    verification_document = Column(Text, nullable=True)
    verification_date = Column(DateTime, nullable=True)
    verified_by = Column(PG_UUID(as_uuid=True), nullable=True)

    scope = Column(Text, nullable=False, default="FULL")

    valid_from = Column(DateTime, nullable=False)
    valid_until = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    audit_log = relationship("GuardianAuditDB", back_populates="guardian")


class GuardianAuditDB(Base):
    __tablename__ = "guardian_audit"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    guardian_id = Column(
        PG_UUID(as_uuid=True), ForeignKey("guardians.id"), nullable=False, index=True
    )

    action = Column(String(100), nullable=False)
    actor_id = Column(PG_UUID(as_uuid=True), nullable=False)
    actor_type = Column(String(50), nullable=False)

    old_status = Column(String(50), nullable=True)
    new_status = Column(String(50), nullable=True)

    details = Column(Text, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    guardian = relationship("GuardianDB", back_populates="audit_log")


class GuardianRegistration(BaseModel):
    guardian_wallet: str = Field(..., min_length=58, max_length=58)
    guardian_name: str
    guardian_email: EmailStr
    guardian_phone: Optional[str] = None
    guardian_type: GuardianType

    principal_id: UUID
    principal_category: PrincipalCategory

    relationship_document: Optional[str] = None
    verification_document: Optional[str] = None

    scope: List[str] = Field(default=["FULL"])
    valid_from: datetime
    valid_until: Optional[datetime] = None


class GuardianAction(BaseModel):
    action: str
    consent_id: Optional[UUID] = None
    details: Optional[dict] = None


class GuardianService:
    def __init__(self, db):
        self.db = db

    async def _log_main_audit(
        self,
        principal_id: Optional[UUID],
        action: str,
        resource_type: str,
        resource_id: UUID,
    ) -> None:
        from api.database import AuditLogDB

        audit = AuditLogDB(
            principal_id=principal_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            created_at=datetime.now(timezone.utc),
        )
        self.db.add(audit)

    async def register_guardian(
        self,
        data: GuardianRegistration,
    ) -> GuardianDB:
        import json

        guardian = GuardianDB(
            id=uuid4(),
            guardian_wallet=data.guardian_wallet,
            guardian_name=data.guardian_name,
            guardian_email=data.guardian_email,
            guardian_phone=data.guardian_phone,
            guardian_type=data.guardian_type,
            principal_id=data.principal_id,
            principal_category=data.principal_category,
            status=GuardianStatus.PENDING_VERIFICATION,
            relationship_document=data.relationship_document,
            verification_document=data.verification_document,
            scope=json.dumps(data.scope),
            valid_from=data.valid_from,
            valid_until=data.valid_until,
        )

        self.db.add(guardian)
        await self._log_main_audit(
            principal_id=data.principal_id,
            action="GUARDIAN_REGISTERED",
            resource_type="guardian",
            resource_id=guardian.id,
        )
        await self.db.commit()
        await self.db.refresh(guardian)

        return guardian

    async def verify_guardian(
        self,
        guardian_id: UUID,
        verifier_id: UUID,
    ) -> GuardianDB:
        result = await self.db.execute(select(GuardianDB).where(GuardianDB.id == guardian_id))
        guardian = result.scalar_one_or_none()

        if not guardian:
            raise ValueError(f"Guardian {guardian_id} not found")

        guardian.status = GuardianStatus.ACTIVE
        guardian.verification_date = datetime.now(timezone.utc)
        guardian.verified_by = verifier_id

        await self._log_audit(
            guardian_id,
            "VERIFIED",
            verifier_id,
            "VERIFIER",
            None,
            GuardianStatus.ACTIVE.value,
        )
        await self._log_main_audit(
            principal_id=guardian.principal_id,
            action="GUARDIAN_VERIFIED",
            resource_type="guardian",
            resource_id=guardian_id,
        )

        await self.db.commit()
        await self.db.refresh(guardian)

        return guardian

    async def get_active_guardian(
        self,
        principal_id: UUID,
    ) -> Optional[GuardianDB]:
        result = await self.db.execute(
            select(GuardianDB).where(
                and_(
                    GuardianDB.principal_id == principal_id,
                    GuardianDB.status == GuardianStatus.ACTIVE,
                )
            )
        )
        return result.scalar_one_or_none()

    async def can_guardian_act(
        self,
        guardian_wallet: str,
        principal_id: UUID,
        action: str,
    ) -> bool:
        result = await self.db.execute(
            select(GuardianDB).where(
                and_(
                    GuardianDB.guardian_wallet == guardian_wallet,
                    GuardianDB.principal_id == principal_id,
                    GuardianDB.status == GuardianStatus.ACTIVE,
                )
            )
        )
        guardian = result.scalar_one_or_none()

        if not guardian:
            return False

        if guardian.valid_until and datetime.now(timezone.utc) > guardian.valid_until:
            guardian.status = GuardianStatus.EXPIRED
            await self.db.commit()
            return False

        return True

    async def log_guardian_action(
        self,
        guardian_id: UUID,
        action: str,
        consent_id: Optional[UUID],
        details: Optional[dict],
    ) -> GuardianAuditDB:
        return await self._log_audit(
            guardian_id,
            action,
            guardian_id,
            "GUARDIAN",
            None,
            None,
            details,
        )

    async def revoke_guardian(
        self,
        guardian_id: UUID,
        reason: str,
        revoked_by: UUID,
    ) -> GuardianDB:
        result = await self.db.execute(select(GuardianDB).where(GuardianDB.id == guardian_id))
        guardian = result.scalar_one_or_none()

        if not guardian:
            raise ValueError(f"Guardian {guardian_id} not found")

        old_status = guardian.status
        guardian.status = GuardianStatus.REVOKED

        await self._log_audit(
            guardian_id,
            "REVOKED",
            revoked_by,
            "ADMIN",
            old_status.value,
            GuardianStatus.REVOKED.value,
            {"reason": reason},
        )

        await self.db.commit()
        await self.db.refresh(guardian)

        return guardian

    async def _log_audit(
        self,
        guardian_id: UUID,
        action: str,
        actor_id: UUID,
        actor_type: str,
        old_status: Optional[str],
        new_status: Optional[str],
        details: Optional[dict] = None,
    ) -> GuardianAuditDB:
        import json

        audit = GuardianAuditDB(
            id=uuid4(),
            guardian_id=guardian_id,
            action=action,
            actor_id=actor_id,
            actor_type=actor_type,
            old_status=old_status,
            new_status=new_status,
            details=json.dumps(details) if details else None,
        )

        self.db.add(audit)
        await self.db.commit()

        return audit

    async def get_guardian_audit_log(
        self,
        guardian_id: UUID,
        limit: int = 50,
    ) -> List[GuardianAuditDB]:
        result = await self.db.execute(
            select(GuardianAuditDB)
            .where(GuardianAuditDB.guardian_id == guardian_id)
            .order_by(GuardianAuditDB.created_at.desc())
            .limit(limit)
        )
        return result.scalars().all()


from sqlalchemy import and_
