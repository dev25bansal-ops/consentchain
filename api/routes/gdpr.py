"""GDPR Compliance API Routes."""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
from typing import Optional, List

from api.dependencies import get_session, verify_fiduciary_api_key
from api.schemas import APIResponse
from api.compliance.gdpr import (
    GDPRConsentValidator,
    GDPRDataSubjectRightsHandler,
    GDPRComplianceChecker,
    GDPRLegalBasis,
    GDPRRights,
)
from api.middleware.rate_limiting import limiter

router = APIRouter(prefix="/api/v1/gdpr", tags=["GDPR"])


class GDPRConsentRequest(BaseModel):
    purpose: str = Field(..., min_length=10, description="Specific purpose for data processing")
    data_types: List[str] = Field(..., description="Categories of personal data")
    legal_basis: str = Field(..., description="GDPR legal basis for processing")
    explicit: bool = Field(False, description="Whether explicit consent is required (Art. 9)")
    age: Optional[int] = Field(None, ge=0, le=150, description="Data subject age")


class DataSubjectRequest(BaseModel):
    principal_id: str = Field(..., description="Data subject identifier")
    right: str = Field(..., description="GDPR right being exercised")
    details: Optional[dict] = Field(None, description="Additional details for the request")


@router.post("/validate-consent", response_model=APIResponse)
@limiter.limit("100/minute")
async def validate_gdpr_consent(
    request: Request,
    body: GDPRConsentRequest,
    fiduciary: dict = Depends(verify_fiduciary_api_key),
):
    """
    Validate that consent meets GDPR requirements.

    GDPR consent must be:
    - Freely given
    - Specific
    - Informed
    - Unambiguous
    - Explicit for special categories (Art. 9)
    """
    is_valid, violations = GDPRConsentValidator.validate_consent(
        purpose=body.purpose,
        data_types=body.data_types,
        legal_basis=body.legal_basis,
        explicit=body.explicit,
        age=body.age,
    )

    retention_days = GDPRConsentValidator.get_retention_period(
        body.purpose, body.legal_basis
    )

    return APIResponse(
        success=is_valid,
        message="Consent is GDPR compliant" if is_valid else "Consent violations found",
        data={
            "valid": is_valid,
            "violations": violations,
            "retention_days": retention_days,
            "legal_basis": body.legal_basis,
        },
    )


@router.post("/data-subject-request", response_model=APIResponse)
@limiter.limit("20/minute")
async def handle_data_subject_request(
    request: Request,
    body: DataSubjectRequest,
    fiduciary: dict = Depends(verify_fiduciary_api_key),
    session: AsyncSession = Depends(get_session),
):
    """
    Handle GDPR data subject rights requests.

    Supported rights:
    - right_to_access (Art. 15)
    - right_to_erasure (Art. 17)
    - right_to_portability (Art. 20)
    - right_to_object (Art. 21)
    """
    handler = GDPRDataSubjectRightsHandler()

    if body.right == GDPRRights.RIGHT_TO_ERASURE.value:
        result = handler.right_to_erasure(
            body.principal_id,
            grounds=body.details.get("grounds") if body.details else None,
        )
    elif body.right == GDPRRights.RIGHT_TO_ACCESS.value:
        result = handler.right_to_access(body.principal_id)
    elif body.right == GDPRRights.RIGHT_TO_DATA_PORTABILITY.value:
        result = handler.right_to_portability(
            body.principal_id,
            format=body.details.get("format", "json") if body.details else "json",
        )
    elif body.right == GDPRRights.RIGHT_TO_OBJECT.value:
        result = handler.right_to_object(
            body.principal_id,
            reason=body.details.get("reason", "") if body.details else "",
        )
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported right: {body.right}. Supported: {[r.value for r in GDPRRights]}",
        )

    return APIResponse(
        success=True,
        message=f"Data subject request '{body.right}' registered",
        data=result,
    )


@router.get("/compliance-status/{fiduciary_id}", response_model=APIResponse)
async def get_gdpr_compliance_status(
    fiduciary_id: str,
    fiduciary: dict = Depends(verify_fiduciary_api_key),
):
    """
    Get GDPR compliance score for a fiduciary.

    Returns detailed compliance assessment with recommendations.
    """
    result = GDPRComplianceChecker.check_compliance(fiduciary_id)

    return APIResponse(
        success=True,
        message=f"GDPR compliance score: {result['score']}% - {result['compliance_level']}",
        data=result,
    )


@router.get("/legal-bases", response_model=APIResponse)
async def list_legal_bases():
    """List all valid GDPR legal bases for processing."""
    return APIResponse(
        success=True,
        message="GDPR legal bases for processing",
        data={
            "legal_bases": [
                {
                    "basis": lb.value,
                    "description": lb.name.replace("_", " ").title(),
                    "article": "Art. 6(1)",
                }
                for lb in GDPRLegalBasis
            ],
            "special_categories": [
                cat.value for cat in [
                    GDPRDataCategory.RACIAL_ETHNIC,
                    GDPRDataCategory.POLITICAL,
                    GDPRDataCategory.RELIGIOUS,
                    GDPRDataCategory.TRADE_UNION,
                    GDPRDataCategory.GENETIC,
                    GDPRDataCategory.BIOMETRIC,
                    GDPRDataCategory.HEALTH,
                    GDPRDataCategory.SEXUAL_ORIENTATION,
                ]
            ],
            "note": "Special categories require explicit consent (Art. 9)",
        },
    )
