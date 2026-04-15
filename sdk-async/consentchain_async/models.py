"""Pydantic models for ConsentChain SDK."""

from datetime import datetime
from uuid import UUID
from typing import Optional, List
from pydantic import BaseModel, Field


class ConsentCreate(BaseModel):
    principal_wallet: str = Field(..., min_length=58, max_length=58)
    fiduciary_id: UUID
    purpose: str
    data_types: List[str]
    expires_at: Optional[datetime] = None
    metadata: Optional[dict] = None


class ConsentUpdate(BaseModel):
    purpose: Optional[str] = None
    data_types: Optional[List[str]] = None
    expires_at: Optional[datetime] = None
    metadata: Optional[dict] = None


class ConsentRecord(BaseModel):
    id: UUID
    principal_id: UUID
    fiduciary_id: UUID
    purpose: str
    data_types: List[str]
    status: str
    granted_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None
    on_chain_tx_id: Optional[str] = None
    on_chain_app_id: Optional[int] = None
    consent_hash: str
    created_at: datetime
    updated_at: Optional[datetime] = None


class Fiduciary(BaseModel):
    id: UUID
    name: str
    registration_number: str
    wallet_address: str
    contact_email: str
    data_categories: List[str]
    purposes: List[str]
    compliance_status: str
    tier: str
    created_at: datetime


class DataPrincipal(BaseModel):
    id: UUID
    wallet_address: str
    email_hash: str
    phone_hash: Optional[str] = None
    kyc_verified: bool
    preferred_language: str
    created_at: datetime


class WebhookSubscription(BaseModel):
    id: UUID
    fiduciary_id: UUID
    callback_url: str
    events: List[str]
    active: bool
    created_at: datetime


class DashboardStats(BaseModel):
    total_consents: int
    active_consents: int
    revoked_consents: int
    expired_consents: int
    total_fiduciaries: int
    total_principals: int
    consent_rate: float
    avg_expiry_days: float


class WebhookDelivery(BaseModel):
    id: UUID
    subscription_id: UUID
    event_type: str
    payload: dict
    status: str
    attempts: int
    last_attempt_at: Optional[datetime] = None
    last_error: Optional[str] = None
    delivered_at: Optional[datetime] = None


class PaginatedResponse(BaseModel, generic=True):
    items: List
    total: int
    page: int
    page_size: int
    pages: int
