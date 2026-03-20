from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field


class APIResponse(BaseModel):
    success: bool
    message: str
    data: Optional[dict] = None


class ConsentCreateRequest(BaseModel):
    principal_wallet: str = Field(..., pattern="^[A-Z0-9]{58}$")
    fiduciary_id: str
    purpose: str
    data_types: list[str]
    duration_days: int = Field(..., ge=1, le=365)
    metadata: dict = Field(default_factory=dict)
    signature: str


class ConsentRevokeRequest(BaseModel):
    consent_id: str
    reason: Optional[str] = None
    signature: str


class ConsentModifyRequest(BaseModel):
    consent_id: str
    new_purpose: Optional[str] = None
    new_data_types: Optional[list[str]] = None
    new_duration_days: Optional[int] = Field(None, ge=1, le=365)
    reason: Optional[str] = None
    signature: str


class ConsentVerifyRequest(BaseModel):
    consent_id: str
    principal_id: Optional[str] = None


class ConsentQueryRequest(BaseModel):
    principal_id: Optional[str] = None
    fiduciary_id: Optional[str] = None
    status: Optional[str] = None
    purpose: Optional[str] = None
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None
    page: int = Field(1, ge=1)
    limit: int = Field(20, ge=1, le=100)


class FiduciaryRegisterRequest(BaseModel):
    name: str
    registration_number: str
    contact_email: str
    data_categories: list[str]
    purposes: list[str]


class AuditQueryRequest(BaseModel):
    principal_id: Optional[str] = None
    fiduciary_id: Optional[str] = None
    consent_id: Optional[str] = None
    event_type: Optional[str] = None
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None
    page: int = Field(1, ge=1)
    limit: int = Field(50, ge=1, le=200)


class ComplianceReportRequest(BaseModel):
    fiduciary_id: str
    period_start: datetime
    period_end: datetime


class WebhookSubscribeRequest(BaseModel):
    callback_url: str
    events: list[str]
    fiduciary_id: str
    secret: str


class BatchConsentCreateRequest(BaseModel):
    consents: list[ConsentCreateRequest]
    batch_id: Optional[str] = None
