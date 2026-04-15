from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from uuid import UUID

from consentchain_types.enums import ConsentStatus, ConsentPurpose, DataType, EventType


class ConsentRecordBase(BaseModel):
    consent_id: UUID
    principal_id: UUID
    fiduciary_id: UUID
    purpose: ConsentPurpose
    data_types: List[DataType]
    status: ConsentStatus = ConsentStatus.PENDING
    granted_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None
    on_chain_tx_id: Optional[str] = None
    consent_hash: str
    created_at: datetime
    updated_at: datetime


class ConsentEventBase(BaseModel):
    event_id: UUID
    consent_id: UUID
    event_type: EventType
    timestamp: datetime
    actor: str
    actor_type: str
    previous_status: Optional[ConsentStatus] = None
    new_status: ConsentStatus
    tx_id: Optional[str] = None


class WebhookPayload(BaseModel):
    event_id: UUID = Field(..., description="Unique event identifier")
    event_type: str = Field(..., description="Event type (e.g., consent.revoked)")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    fiduciary_id: UUID
    data: Dict[str, Any] = Field(default_factory=dict)
    signature: Optional[str] = None

    class Config:
        json_encoders = {
            UUID: lambda v: str(v),
            datetime: lambda v: v.isoformat(),
        }
