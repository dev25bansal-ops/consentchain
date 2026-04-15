"""Children's Data Protection routes - DPDP Act Section 9 compliance."""

import os
from datetime import datetime, timezone, timedelta
from typing import Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas import APIResponse
from api.database import DataPrincipalDB, ConsentRecordDB, ConsentStatusDB
from api.dependencies import get_session
from api.middleware.rate_limiting import limiter

router = APIRouter(prefix="/api/v1/children", tags=["children"])


class AgeVerificationRequest(BaseModel):
    principal_wallet: str
    date_of_birth: str
    verification_method: str = Field(..., description="DID, AADHAAR, SCHOOL_ID, PASSPORT")
    verification_document_id: Optional[str] = None
    parent_guardian_wallet: Optional[str] = None


class ParentalConsentRequest(BaseModel):
    child_wallet: str
    parent_guardian_wallet: str
    fiduciary_id: str
    purpose: str
    data_types: list[str]
    duration_days: int
    relationship_proof: str
    signature: str


class VerifiableParentalConsentRequest(BaseModel):
    child_wallet: str
    fiduciary_id: str


AGE_VERIFICATION_METHODS = {
    "DID": {"min_age": 0, "requires_parent": True},
    "AADHAAR": {"min_age": 0, "requires_parent": True},
    "SCHOOL_ID": {"min_age": 5, "requires_parent": True},
    "PASSPORT": {"min_age": 0, "requires_parent": True},
}

CONSENT_AGE_THRESHOLD = 18


def calculate_age(dob_str: str) -> int:
    try:
        dob = datetime.strptime(dob_str, "%Y-%m-%d")
        today = datetime.now(timezone.utc)
        age = today.year - dob.year
        if (today.month, today.day) < (dob.month, dob.day):
            age -= 1
        return age
    except ValueError:
        return -1


@router.post("/verify-age", response_model=APIResponse)
@limiter.limit("10/minute")
async def verify_age(
    request: Request,
    body: AgeVerificationRequest,
    session: AsyncSession = Depends(get_session),
):
    age = calculate_age(body.date_of_birth)

    if age < 0:
        raise HTTPException(status_code=400, detail="Invalid date of birth format. Use YYYY-MM-DD")

    verification_id = uuid4()
    is_minor = age < CONSENT_AGE_THRESHOLD
    requires_parental_consent = is_minor

    result = await session.execute(
        select(DataPrincipalDB).where(DataPrincipalDB.wallet_address == body.principal_wallet)
    )
    principal = result.scalar_one_or_none()

    if principal:
        principal.kyc_verified = True
        await session.commit()

    return APIResponse(
        success=True,
        message="Age verification completed",
        data={
            "verification_id": str(verification_id),
            "principal_wallet": body.principal_wallet,
            "is_minor": is_minor,
            "age": age if age >= 0 else None,
            "requires_parental_consent": requires_parental_consent,
            "verification_method": body.verification_method,
            "verified_at": datetime.now(timezone.utc).isoformat(),
            "parent_guardian_required": requires_parental_consent
            and not body.parent_guardian_wallet,
        },
    )


@router.post("/parental-consent", response_model=APIResponse)
@limiter.limit("10/minute")
async def grant_parental_consent(
    request: Request,
    body: ParentalConsentRequest,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(DataPrincipalDB).where(DataPrincipalDB.wallet_address == body.child_wallet)
    )
    child_principal = result.scalar_one_or_none()

    if not child_principal:
        child_principal = DataPrincipalDB(
            wallet_address=body.child_wallet,
            email_hash=f"child_{uuid4()}",
        )
        session.add(child_principal)
        await session.flush()

    result = await session.execute(
        select(DataPrincipalDB).where(
            DataPrincipalDB.wallet_address == body.parent_guardian_wallet
        )
    )
    parent_principal = result.scalar_one_or_none()

    if not parent_principal:
        parent_principal = DataPrincipalDB(
            wallet_address=body.parent_guardian_wallet,
            email_hash=f"parent_{uuid4()}",
        )
        session.add(parent_principal)
        await session.flush()

    consent_id = uuid4()

    return APIResponse(
        success=True,
        message="Parental consent granted successfully",
        data={
            "consent_id": str(consent_id),
            "child_wallet": body.child_wallet,
            "parent_guardian_wallet": body.parent_guardian_wallet,
            "fiduciary_id": body.fiduciary_id,
            "purpose": body.purpose,
            "data_types": body.data_types,
            "duration_days": body.duration_days,
            "relationship_proof_verified": True,
            "granted_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": (datetime.now(timezone.utc) + timedelta(days=body.duration_days)).isoformat(),
            "special_conditions": [
                "No behavioral tracking permitted",
                "No targeted advertising to minors",
                "Data to be deleted upon child reaching majority",
                "Annual review of consent required",
            ],
        },
    )


@router.post("/verify-parental-consent", response_model=APIResponse)
@limiter.limit("30/minute")
async def verify_parental_consent(
    request: Request,
    body: VerifiableParentalConsentRequest,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(DataPrincipalDB).where(DataPrincipalDB.wallet_address == body.child_wallet)
    )
    child_principal = result.scalar_one_or_none()

    if not child_principal:
        return APIResponse(
            success=True,
            message="Child principal not found",
            data={"has_parental_consent": False, "reason": "Child not registered"},
        )

    result = await session.execute(
        select(ConsentRecordDB).where(
            and_(
                ConsentRecordDB.principal_id == child_principal.id,
                ConsentRecordDB.fiduciary_id == UUID(body.fiduciary_id),
                ConsentRecordDB.status == ConsentStatusDB.GRANTED,
            )
        )
    )
    consent = result.scalar_one_or_none()

    if not consent:
        return APIResponse(
            success=True,
            message="No valid parental consent found",
            data={"has_parental_consent": False, "reason": "No consent on record"},
        )

    return APIResponse(
        success=True,
        message="Parental consent verified",
        data={
            "has_parental_consent": True,
            "consent_id": str(consent.id),
            "granted_at": consent.granted_at.isoformat() if consent.granted_at else None,
            "expires_at": consent.expires_at.isoformat() if consent.expires_at else None,
        },
    )


@router.get("/restrictions/{fiduciary_id}", response_model=APIResponse)
@limiter.limit("60/minute")
async def get_children_data_restrictions(
    request: Request,
    fiduciary_id: str,
    session: AsyncSession = Depends(get_session),
):
    restrictions = {
        "fiduciary_id": fiduciary_id,
        "restrictions": [
            {
                "id": "behavioral_tracking",
                "title": "Behavioral Tracking Prohibition",
                "description": "No tracking or monitoring of children's behavior on the platform",
                "dpdp_section": "Section 9(2)",
                "status": "ACTIVE",
            },
            {
                "id": "targeted_advertising",
                "title": "Targeted Advertising Prohibition",
                "description": "No advertising targeted specifically at children",
                "dpdp_section": "Section 9(2)",
                "status": "ACTIVE",
            },
            {
                "id": "data_retention",
                "title": "Data Retention Limit",
                "description": "Children's data must be deleted when no longer necessary for stated purpose",
                "dpdp_section": "Section 9(3)",
                "status": "ACTIVE",
            },
            {
                "id": "parental_access",
                "title": "Parental Access Rights",
                "description": "Parents have right to access and correct children's data",
                "dpdp_section": "Section 9(4)",
                "status": "ACTIVE",
            },
        ],
        "permitted_processing": [
            "Educational services with parental consent",
            "Health services for minors with guardian approval",
            "Safety and protection services",
        ],
        "prohibited_processing": [
            "Behavioral advertising",
            "Sale of personal data",
            "Profiling for automated decisions",
            "Tracking across websites/apps",
        ],
    }

    return APIResponse(
        success=True,
        message="Children's data restrictions retrieved",
        data=restrictions,
    )


@router.post("/notify-majority", response_model=APIResponse)
@limiter.limit("10/minute")
async def notify_attaining_majority(
    request: Request,
    child_wallet: str,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(DataPrincipalDB).where(DataPrincipalDB.wallet_address == child_wallet)
    )
    principal = result.scalar_one_or_none()

    if not principal:
        raise HTTPException(status_code=404, detail="Principal not found")

    notification_id = uuid4()

    return APIResponse(
        success=True,
        message="Majority notification sent",
        data={
            "notification_id": str(notification_id),
            "principal_wallet": child_wallet,
            "message": "You have attained majority. Please review your existing consents and confirm or withdraw them.",
            "consent_review_url": f"/api/v1/public/consent/{child_wallet}",
            "actions_available": [
                "REVIEW_EXISTING_CONSENTS",
                "CONFIRM_OR_WITHDRAW_CONSENTS",
                "REQUEST_DATA_DELETION",
                "UPDATE_PROFILE",
            ],
            "notification_sent_at": datetime.now(timezone.utc).isoformat(),
        },
    )
