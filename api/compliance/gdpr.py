"""GDPR Compliance Module - Extends DPDP compliance to GDPR."""

from enum import Enum
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional


class GDPRLegalBasis(str, Enum):
    CONSENT = "consent"
    CONTRACT = "contract"
    LEGAL_OBLIGATION = "legal_obligation"
    VITAL_INTERESTS = "vital_interests"
    PUBLIC_TASK = "public_task"
    LEGITIMATE_INTERESTS = "legitimate_interests"


class GDPRDataCategory(str, Enum):
    IDENTITY = "identity"
    CONTACT = "contact"
    FINANCIAL = "financial"
    # Special category data (GDPR Art. 9)
    RACIAL_ETHNIC = "racial_ethnic"
    POLITICAL = "political"
    RELIGIOUS = "religious"
    TRADE_UNION = "trade_union"
    GENETIC = "genetic"
    BIOMETRIC = "biometric"
    HEALTH = "health"
    SEXUAL_ORIENTATION = "sexual_orientation"


class GDPRRights(str, Enum):
    RIGHT_TO_ACCESS = "right_to_access"
    RIGHT_TO_RECTIFICATION = "right_to_rectification"
    RIGHT_TO_ERASURE = "right_to_erasure"
    RIGHT_TO_RESTRICT_PROCESSING = "right_to_restrict"
    RIGHT_TO_DATA_PORTABILITY = "right_to_portability"
    RIGHT_TO_OBJECT = "right_to_object"
    RIGHTS_RELATED_TO_AUTOMATED_DECISION_MAKING = "right_no_automated_decisions"


class GDPRConsentValidator:
    """Validates consent meets GDPR standards (stricter than DPDP)."""

    SPECIAL_CATEGORIES = [
        GDPRDataCategory.RACIAL_ETHNIC.value,
        GDPRDataCategory.POLITICAL.value,
        GDPRDataCategory.RELIGIOUS.value,
        GDPRDataCategory.TRADE_UNION.value,
        GDPRDataCategory.GENETIC.value,
        GDPRDataCategory.BIOMETRIC.value,
        GDPRDataCategory.HEALTH.value,
        GDPRDataCategory.SEXUAL_ORIENTATION.value,
    ]

    RETENTION_PERIODS = {
        GDPRLegalBasis.CONSENT.value: 365,
        GDPRLegalBasis.CONTRACT.value: 730,
        GDPRLegalBasis.LEGAL_OBLIGATION.value: 2555,
        GDPRLegalBasis.VITAL_INTERESTS.value: 365,
        GDPRLegalBasis.PUBLIC_TASK.value: 730,
        GDPRLegalBasis.LEGITIMATE_INTERESTS.value: 365,
    }

    @classmethod
    def validate_consent(
        cls,
        purpose: str,
        data_types: List[str],
        legal_basis: str,
        explicit: bool = False,
        age: Optional[int] = None
    ) -> tuple[bool, List[str]]:
        """
        Validate GDPR consent requirements.

        GDPR requires:
        - Freely given (no bundled consent)
        - Specific (clear purpose)
        - Informed (user knows what they're consenting to)
        - Unambiguous (clear affirmative action)
        - Explicit required for special categories (Art. 9)
        - Age verification (16+, or parental consent for 13-16)
        - Easy to withdraw
        """
        violations = []

        # Check legal basis is valid
        valid_bases = [b.value for b in GDPRLegalBasis]
        if legal_basis not in valid_bases:
            violations.append(f"Invalid legal basis: {legal_basis}. Must be one of: {valid_bases}")

        # Explicit consent required for special category data (Art. 9)
        has_special = any(dt in cls.SPECIAL_CATEGORIES for dt in data_types)
        if has_special and not explicit:
            violations.append("Explicit consent required for special category data (GDPR Art. 9)")

        # Age verification
        if age is not None:
            if age < 13:
                violations.append("Under 13: parental consent required (GDPR Art. 8)")
            elif age < 16:
                violations.append("Age 13-16: parental consent may be required (varies by EU member state)")

        # Purpose must be specific
        if not purpose or len(purpose.strip()) < 10:
            violations.append("Purpose must be specific and clearly stated (min 10 characters)")

        # Data minimization check
        if len(data_types) > 10:
            violations.append(f"Too many data types ({len(data_types)}). Review data minimization principle")

        return len(violations) == 0, violations

    @classmethod
    def get_retention_period(cls, purpose: str, legal_basis: str) -> int:
        """Get maximum retention period in days under GDPR."""
        return cls.RETENTION_PERIODS.get(legal_basis, 365)


class GDPRDataSubjectRightsHandler:
    """Handles GDPR data subject rights requests."""

    @staticmethod
    def right_to_access(principal_id: str) -> Dict[str, Any]:
        """
        Art. 15: Right of access by the data subject.

        Return all personal data held about the user.
        """
        return {
            "right": GDPRRights.RIGHT_TO_ACCESS.value,
            "principal_id": principal_id,
            "data_categories": [],
            "purposes": [],
            "recipients": [],
            "retention_period": None,
            "source": "collected_from_data_subject",
            "note": "This request must be fulfilled within 1 month (Art. 12)",
        }

    @staticmethod
    def right_to_rectification(principal_id: str, corrections: Dict[str, Any]) -> Dict[str, Any]:
        """
        Art. 16: Right to rectification.
        """
        return {
            "right": GDPRRights.RIGHT_TO_RECTIFICATION.value,
            "principal_id": principal_id,
            "corrections": corrections,
            "status": "pending",
            "deadline": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
        }

    @staticmethod
    def right_to_erasure(principal_id: str, grounds: List[str] = None) -> Dict[str, Any]:
        """
        Art. 17: Right to erasure ('right to be forgotten').

        More comprehensive than DPDP deletion.
        """
        valid_grounds = [
            "consent_withdrawn",
            "data_no_longer_necessary",
            "objection_to_processing",
            "unlawful_processing",
            "legal_obligation",
            "child_information_services",
        ]

        return {
            "right": GDPRRights.RIGHT_TO_ERASURE.value,
            "principal_id": principal_id,
            "grounds": grounds or [],
            "valid_grounds": valid_grounds,
            "status": "pending",
            "completion_deadline": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
        }

    @staticmethod
    def right_to_portability(principal_id: str, format: str = "json") -> Dict[str, Any]:
        """
        Art. 20: Right to data portability.

        Provide data in structured, commonly used, machine-readable format.
        """
        return {
            "right": GDPRRights.RIGHT_TO_DATA_PORTABILITY.value,
            "principal_id": principal_id,
            "format": format,
            "status": "pending",
            "deadline": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
        }

    @staticmethod
    def right_to_object(principal_id: str, reason: str) -> Dict[str, Any]:
        """
        Art. 21: Right to object to processing.
        """
        return {
            "right": GDPRRights.RIGHT_TO_OBJECT.value,
            "principal_id": principal_id,
            "reason": reason,
            "status": "pending",
            "note": "Processing must stop unless compelling legitimate grounds override",
        }


class GDPRComplianceChecker:
    """Checks overall GDPR compliance of the system."""

    REQUIRED_CHECKS = {
        "consent_valid": "GDPR-compliant consent mechanism",
        "privacy_policy_present": "Clear privacy policy provided",
        "dpo_appointed": "Data Protection Officer appointed",
        "data_protection_impact_assessment": "DPIA conducted for high-risk processing",
        "breach_notification_procedure": "72-hour breach notification procedure",
        "data_processing_records": "Records of processing activities maintained",
        "international_transfers_documented": "International transfer mechanisms documented",
        "data_subject_rights_process": "Process for handling data subject rights",
        "data_minimization": "Data minimization principles applied",
        "purpose_limitation": "Purpose limitation respected",
    }

    @classmethod
    def check_compliance(cls, fiduciary_id: str) -> Dict[str, Any]:
        """Run GDPR compliance checks and return score."""
        # In production, these would check actual system state
        checks = {
            "consent_valid": True,
            "privacy_policy_present": True,
            "dpo_appointed": False,
            "data_protection_impact_assessment": False,
            "breach_notification_procedure": True,
            "data_processing_records": False,
            "international_transfers_documented": True,
            "data_subject_rights_process": True,
            "data_minimization": True,
            "purpose_limitation": True,
        }

        score = sum(1 for v in checks.values() if v) / len(checks) * 100

        recommendations = []
        for check, passed in checks.items():
            if not passed:
                recommendations.append(
                    f"Implement: {cls.REQUIRED_CHECKS.get(check, check)}"
                )

        return {
            "framework": "GDPR",
            "fiduciary_id": fiduciary_id,
            "score": round(score, 2),
            "total_checks": len(checks),
            "passed_checks": sum(1 for v in checks.values() if v),
            "failed_checks": sum(1 for v in checks.values() if not v),
            "checks": checks,
            "recommendations": recommendations,
            "compliance_level": cls._get_compliance_level(score),
        }

    @staticmethod
    def _get_compliance_level(score: float) -> str:
        if score >= 90:
            return "Excellent"
        elif score >= 70:
            return "Good"
        elif score >= 50:
            return "Partial"
        else:
            return "Non-Compliant"
