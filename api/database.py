from sqlalchemy import Column, String, DateTime, Boolean, Integer, Text, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from uuid import uuid4
from datetime import datetime
import enum

Base = declarative_base()


class ConsentStatusDB(enum.Enum):
    GRANTED = "GRANTED"
    REVOKED = "REVOKED"
    MODIFIED = "MODIFIED"
    PENDING = "PENDING"
    EXPIRED = "EXPIRED"


class EventTypeDB(enum.Enum):
    CONSENT_GRANTED = "CONSENT_GRANTED"
    CONSENT_REVOKED = "CONSENT_REVOKED"
    CONSENT_MODIFIED = "CONSENT_MODIFIED"
    DATA_ACCESS = "DATA_ACCESS"
    DATA_DELETION = "DATA_DELETION"


class DataPrincipalDB(Base):
    __tablename__ = "data_principals"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    wallet_address = Column(String(58), unique=True, nullable=False, index=True)
    email_hash = Column(String(64), nullable=False)
    phone_hash = Column(String(64), nullable=True)
    kyc_verified = Column(Boolean, default=False)
    preferred_language = Column(String(10), default="en")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    consents = relationship("ConsentRecordDB", back_populates="principal")
    audit_logs = relationship("AuditLogDB", back_populates="principal")


class DataFiduciaryDB(Base):
    __tablename__ = "data_fiduciaries"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(255), nullable=False)
    registration_number = Column(String(100), unique=True, nullable=False)
    wallet_address = Column(String(58), unique=True, nullable=False)
    contact_email = Column(String(255), nullable=False)
    api_key_hash = Column(String(64), nullable=False)
    data_categories = Column(Text, nullable=False)
    purposes = Column(Text, nullable=False)
    compliance_status = Column(String(50), default="ACTIVE")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    consents = relationship("ConsentRecordDB", back_populates="fiduciary")
    audit_logs = relationship("AuditLogDB", back_populates="fiduciary")


class ConsentRecordDB(Base):
    __tablename__ = "consent_records"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    principal_id = Column(PG_UUID(as_uuid=True), ForeignKey("data_principals.id"), nullable=False)
    fiduciary_id = Column(PG_UUID(as_uuid=True), ForeignKey("data_fiduciaries.id"), nullable=False)
    purpose = Column(String(50), nullable=False)
    data_types = Column(Text, nullable=False)
    status = Column(SQLEnum(ConsentStatusDB), default=ConsentStatusDB.PENDING)
    granted_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    revoked_at = Column(DateTime, nullable=True)
    on_chain_tx_id = Column(String(64), nullable=True)
    on_chain_app_id = Column(Integer, nullable=True)
    consent_hash = Column(String(64), nullable=False)
    metadata = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    principal = relationship("DataPrincipalDB", back_populates="consents")
    fiduciary = relationship("DataFiduciaryDB", back_populates="consents")
    events = relationship("ConsentEventDB", back_populates="consent")


class ConsentEventDB(Base):
    __tablename__ = "consent_events"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    consent_id = Column(PG_UUID(as_uuid=True), ForeignKey("consent_records.id"), nullable=False)
    event_type = Column(SQLEnum(EventTypeDB), nullable=False)
    actor = Column(String(58), nullable=False)
    actor_type = Column(String(50), nullable=False)
    previous_status = Column(SQLEnum(ConsentStatusDB), nullable=True)
    new_status = Column(SQLEnum(ConsentStatusDB), nullable=False)
    tx_id = Column(String(64), nullable=True)
    block_number = Column(Integer, nullable=True)
    ipfs_hash = Column(String(100), nullable=True)
    signature = Column(Text, nullable=True)
    metadata = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    consent = relationship("ConsentRecordDB", back_populates="events")


class AuditLogDB(Base):
    __tablename__ = "audit_logs"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    principal_id = Column(PG_UUID(as_uuid=True), ForeignKey("data_principals.id"), nullable=True)
    fiduciary_id = Column(PG_UUID(as_uuid=True), ForeignKey("data_fiduciaries.id"), nullable=True)
    action = Column(String(100), nullable=False)
    resource_type = Column(String(50), nullable=False)
    resource_id = Column(PG_UUID(as_uuid=True), nullable=False)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    on_chain_reference = Column(String(100), nullable=True)
    verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    principal = relationship("DataPrincipalDB", back_populates="audit_logs")
    fiduciary = relationship("DataFiduciaryDB", back_populates="audit_logs")


class MerkleRootDB(Base):
    __tablename__ = "merkle_roots"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    root_hash = Column(String(64), unique=True, nullable=False)
    event_count = Column(Integer, nullable=False)
    first_event_id = Column(PG_UUID(as_uuid=True), nullable=True)
    last_event_id = Column(PG_UUID(as_uuid=True), nullable=True)
    on_chain_tx_id = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class ComplianceReportDB(Base):
    __tablename__ = "compliance_reports"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    fiduciary_id = Column(PG_UUID(as_uuid=True), ForeignKey("data_fiduciaries.id"), nullable=False)
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    total_consents = Column(Integer, default=0)
    active_consents = Column(Integer, default=0)
    revoked_consents = Column(Integer, default=0)
    expired_consents = Column(Integer, default=0)
    sensitive_data_consents = Column(Integer, default=0)
    third_party_sharing_count = Column(Integer, default=0)
    audit_events = Column(Integer, default=0)
    compliance_score = Column(Integer, default=0)
    on_chain_hash = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
