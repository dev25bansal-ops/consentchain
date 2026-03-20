from enum import Enum
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from uuid import UUID, uuid4


class ConsentStatus(str, Enum):
    GRANTED = "GRANTED"
    REVOKED = "REVOKED"
    MODIFIED = "MODIFIED"
    PENDING = "PENDING"
    EXPIRED = "EXPIRED"


class ConsentPurpose(str, Enum):
    MARKETING = "MARKETING"
    ANALYTICS = "ANALYTICS"
    SERVICE_DELIVERY = "SERVICE_DELIVERY"
    THIRD_PARTY_SHARING = "THIRD_PARTY_SHARING"
    RESEARCH = "RESEARCH"
    COMPLIANCE = "COMPLIANCE"
    PAYMENT_PROCESSING = "PAYMENT_PROCESSING"


class DataType(str, Enum):
    PERSONAL_INFO = "PERSONAL_INFO"
    CONTACT_INFO = "CONTACT_INFO"
    FINANCIAL_DATA = "FINANCIAL_DATA"
    HEALTH_DATA = "HEALTH_DATA"
    LOCATION_DATA = "LOCATION_DATA"
    BEHAVIORAL_DATA = "BEHAVIORAL_DATA"
    BIOMETRIC_DATA = "BIOMETRIC_DATA"
    SENSITIVE_DATA = "SENSITIVE_DATA"


class EventType(str, Enum):
    CONSENT_GRANTED = "CONSENT_GRANTED"
    CONSENT_REVOKED = "CONSENT_REVOKED"
    CONSENT_MODIFIED = "CONSENT_MODIFIED"
    DATA_ACCESS = "DATA_ACCESS"
    DATA_DELETION = "DATA_DELETION"
    CONSENT_EXPIRY = "CONSENT_EXPIRY"


class DataPrincipal(BaseModel):
    user_id: UUID = Field(default_factory=uuid4)
    wallet_address: str
    email_hash: str
    phone_hash: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    kyc_verified: bool = False
    preferred_language: str = "en"


class DataFiduciary(BaseModel):
    fiduciary_id: UUID = Field(default_factory=uuid4)
    name: str
    registration_number: str
    wallet_address: str
    contact_email: str
    data_categories: List[DataType]
    purposes: List[ConsentPurpose]
    api_key_hash: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    compliance_status: str = "ACTIVE"


class ConsentRecord(BaseModel):
    consent_id: UUID = Field(default_factory=uuid4)
    principal_id: UUID
    fiduciary_id: UUID
    purpose: ConsentPurpose
    data_types: List[DataType]
    status: ConsentStatus = ConsentStatus.PENDING
    granted_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None
    on_chain_tx_id: Optional[str] = None
    on_chain_app_id: Optional[int] = None
    consent_hash: str
    metadata: dict = {}
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ConsentEvent(BaseModel):
    event_id: UUID = Field(default_factory=uuid4)
    consent_id: UUID
    event_type: EventType
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    actor: str
    actor_type: str
    previous_status: Optional[ConsentStatus] = None
    new_status: ConsentStatus
    tx_id: Optional[str] = None
    block_number: Optional[int] = None
    ipfs_hash: Optional[str] = None
    signature: Optional[str] = None
    metadata: dict = {}


class AuditLog(BaseModel):
    log_id: UUID = Field(default_factory=uuid4)
    event_id: UUID
    principal_id: UUID
    fiduciary_id: UUID
    action: str
    resource_type: str
    resource_id: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    on_chain_reference: Optional[str] = None
    verified: bool = False


class ConsentRequest(BaseModel):
    principal_wallet: str = Field(..., pattern="^[A-Z0-9]{58}$")
    fiduciary_id: UUID
    purpose: ConsentPurpose
    data_types: List[DataType]
    duration_days: int = Field(..., ge=1, le=365)
    metadata: dict = {}


class ConsentUpdate(BaseModel):
    consent_id: UUID
    action: str
    new_purpose: Optional[ConsentPurpose] = None
    new_data_types: Optional[List[DataType]] = None
    new_duration_days: Optional[int] = Field(None, ge=1, le=365)
    reason: Optional[str] = None


class ConsentQuery(BaseModel):
    principal_id: Optional[UUID] = None
    fiduciary_id: Optional[UUID] = None
    status: Optional[ConsentStatus] = None
    purpose: Optional[ConsentPurpose] = None
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None
    page: int = Field(1, ge=1)
    limit: int = Field(20, ge=1, le=100)


class ComplianceReport(BaseModel):
    report_id: UUID = Field(default_factory=uuid4)
    fiduciary_id: UUID
    period_start: datetime
    period_end: datetime
    total_consents: int
    active_consents: int
    revoked_consents: int
    expired_consents: int
    sensitive_data_consents: int
    third_party_sharing_count: int
    audit_events: int
    compliance_score: float
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    on_chain_hash: Optional[str] = None
