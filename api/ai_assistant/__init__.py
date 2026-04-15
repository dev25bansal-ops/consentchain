from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import json
import re
import logging

logger = logging.getLogger(__name__)


class SuggestionCategory(str, Enum):
    PURPOSE = "purpose"
    DATA_TYPE = "data_type"
    DURATION = "duration"
    RETENTION = "retention"
    COMPLIANCE = "compliance"
    SECURITY = "security"


@dataclass
class ComplianceSuggestion:
    category: SuggestionCategory
    title: str
    description: str
    recommendation: str
    severity: str  # "info", "warning", "critical"
    dpdp_section: Optional[str] = None
    best_practice: Optional[str] = None
    auto_fix: Optional[Dict[str, Any]] = None


@dataclass
class ConsentAnalysis:
    purpose_valid: bool
    data_types_appropriate: bool
    duration_reasonable: bool
    compliance_score: float  # 0-100
    suggestions: List[ComplianceSuggestion]
    warnings: List[str]
    dpdp_compliance: Dict[str, bool]


DPDP_PROVISIONS = {
    "Section 4": "Consent must be free, specific, informed, unconditional, and unambiguous",
    "Section 5": "Purpose limitation - data can only be processed for stated purposes",
    "Section 6": "Data minimization - collect only necessary data",
    "Section 7": "Storage limitation - retain data only as long as necessary",
    "Section 8": "Right to withdraw consent at any time",
    "Section 9": "Right to erasure within 30 days of request",
    "Section 10": "Right to access personal data",
    "Section 11": "Right to correction of inaccurate data",
    "Section 12": "Cross-border transfer restrictions",
    "Section 17": "Breach notification within 72 hours",
}

SENSITIVE_DATA_TYPES = {
    "health_data": {
        "requires_explicit_consent": True,
        "restricted_purposes": ["MARKETING", "THIRD_PARTY_SHARING"],
        "recommended_duration_days": 90,
        "dpdp_note": "Health data requires additional safeguards under DPDP",
    },
    "biometric_data": {
        "requires_explicit_consent": True,
        "restricted_purposes": ["MARKETING", "THIRD_PARTY_SHARING", "ANALYTICS"],
        "recommended_duration_days": 30,
        "dpdp_note": "Biometric data is highly sensitive and should have strict limitations",
    },
    "financial_data": {
        "requires_explicit_consent": True,
        "restricted_purposes": ["MARKETING"],
        "recommended_duration_days": 180,
        "dpdp_note": "Financial data requires explicit consent for sharing",
    },
    "location_data": {
        "requires_explicit_consent": True,
        "restricted_purposes": ["MARKETING"],
        "recommended_duration_days": 90,
        "dpdp_note": "Location tracking should be transparent with opt-out options",
    },
}

PURPOSE_DURATIONS = {
    "MARKETING": {"min_days": 1, "recommended_days": 180, "max_days": 365},
    "ANALYTICS": {"min_days": 30, "recommended_days": 365, "max_days": 730},
    "SERVICE_DELIVERY": {"min_days": 30, "recommended_days": 730, "max_days": 1095},
    "THIRD_PARTY_SHARING": {"min_days": 1, "recommended_days": 90, "max_days": 365},
    "RESEARCH": {"min_days": 90, "recommended_days": 730, "max_days": 1825},
    "COMPLIANCE": {"min_days": 365, "recommended_days": 2555, "max_days": 3650},
    "PAYMENT_PROCESSING": {"min_days": 30, "recommended_days": 365, "max_days": 730},
}

PURPOSE_DATA_TYPE_GUIDELINES = {
    "MARKETING": {
        "recommended": ["contact_info", "personal_info"],
        "allowed": ["behavioral_data", "location_data"],
        "restricted": ["health_data", "biometric_data", "financial_data"],
    },
    "SERVICE_DELIVERY": {
        "recommended": ["personal_info", "contact_info"],
        "allowed": ["financial_data", "location_data"],
        "restricted": ["biometric_data"],
    },
    "ANALYTICS": {
        "recommended": ["behavioral_data", "personal_info"],
        "allowed": ["location_data", "contact_info"],
        "restricted": ["health_data", "biometric_data"],
    },
    "THIRD_PARTY_SHARING": {
        "recommended": ["personal_info", "contact_info"],
        "allowed": ["financial_data"],
        "restricted": ["health_data", "biometric_data", "location_data"],
    },
    "RESEARCH": {
        "recommended": ["personal_info", "behavioral_data"],
        "allowed": ["health_data", "location_data"],
        "restricted": ["biometric_data"],
    },
    "COMPLIANCE": {
        "recommended": ["personal_info", "financial_data"],
        "allowed": ["contact_info", "health_data"],
        "restricted": ["biometric_data"],
    },
    "PAYMENT_PROCESSING": {
        "recommended": ["financial_data", "personal_info"],
        "allowed": ["contact_info"],
        "restricted": ["health_data", "biometric_data", "location_data"],
    },
}


class AIComplianceAssistant:
    def __init__(self):
        self.dpdp_provisions = DPDP_PROVISIONS
        self.sensitive_data = SENSITIVE_DATA_TYPES
        self.purpose_durations = PURPOSE_DURATIONS
        self.purpose_guidelines = PURPOSE_DATA_TYPE_GUIDELINES

    def analyze_consent(
        self,
        purpose: str,
        data_types: List[str],
        duration_days: int,
        fiduciary_type: Optional[str] = None,
        cross_border: bool = False,
    ) -> ConsentAnalysis:
        suggestions: List[ComplianceSuggestion] = []
        warnings: List[str] = []
        dpdp_compliance: Dict[str, bool] = {}

        purpose_valid = self._validate_purpose(purpose, suggestions, warnings)
        data_appropriate = self._validate_data_types(purpose, data_types, suggestions, warnings)
        duration_reasonable = self._validate_duration(purpose, duration_days, suggestions, warnings)

        self._check_sensitive_data(data_types, purpose, suggestions, warnings)
        self._check_cross_border(cross_border, suggestions, warnings)

        for section, description in self.dpdp_provisions.items():
            dpdp_compliance[section] = self._check_dpdp_section(
                section, purpose, data_types, duration_days
            )

        score = self._calculate_compliance_score(
            purpose_valid, data_appropriate, duration_reasonable, suggestions
        )

        return ConsentAnalysis(
            purpose_valid=purpose_valid,
            data_types_appropriate=data_appropriate,
            duration_reasonable=duration_reasonable,
            compliance_score=score,
            suggestions=suggestions,
            warnings=warnings,
            dpdp_compliance=dpdp_compliance,
        )

    def _validate_purpose(
        self,
        purpose: str,
        suggestions: List[ComplianceSuggestion],
        warnings: List[str],
    ) -> bool:
        if purpose not in self.purpose_durations:
            warnings.append(f"Purpose '{purpose}' is not a standard consent purpose")
            suggestions.append(
                ComplianceSuggestion(
                    category=SuggestionCategory.PURPOSE,
                    title="Non-standard Purpose",
                    description=f"The purpose '{purpose}' is not in the standard list",
                    recommendation="Consider using a standard purpose: MARKETING, ANALYTICS, SERVICE_DELIVERY, THIRD_PARTY_SHARING, RESEARCH, COMPLIANCE, PAYMENT_PROCESSING",
                    severity="warning",
                    dpdp_section="Section 5",
                )
            )
            return False
        return True

    def _validate_data_types(
        self,
        purpose: str,
        data_types: List[str],
        suggestions: List[ComplianceSuggestion],
        warnings: List[str],
    ) -> bool:
        if not data_types:
            warnings.append("No data types specified")
            return False

        guidelines = self.purpose_guidelines.get(purpose, {})
        restricted = guidelines.get("restricted", [])
        recommended = guidelines.get("recommended", [])

        appropriate = True
        for dt in data_types:
            if dt in restricted:
                appropriate = False
                warnings.append(f"Data type '{dt}' is restricted for purpose '{purpose}'")
                suggestions.append(
                    ComplianceSuggestion(
                        category=SuggestionCategory.DATA_TYPE,
                        title="Restricted Data Type",
                        description=f"'{dt}' should not be used for {purpose}",
                        recommendation=f"Remove '{dt}' from data types or change the purpose",
                        severity="critical",
                        dpdp_section="Section 6",
                        auto_fix={"remove_data_type": dt},
                    )
                )

        recommended_not_used = [dt for dt in recommended if dt not in data_types]
        if recommended_not_used and not restricted:
            suggestions.append(
                ComplianceSuggestion(
                    category=SuggestionCategory.DATA_TYPE,
                    title="Recommended Data Types Missing",
                    description=f"Consider adding: {', '.join(recommended_not_used)}",
                    recommendation="Include recommended data types for better consent coverage",
                    severity="info",
                )
            )

        return appropriate

    def _validate_duration(
        self,
        purpose: str,
        duration_days: int,
        suggestions: List[ComplianceSuggestion],
        warnings: List[str],
    ) -> bool:
        duration_guidelines = self.purpose_durations.get(purpose)
        if not duration_guidelines:
            return True

        min_days = duration_guidelines["min_days"]
        max_days = duration_guidelines["max_days"]
        recommended_days = duration_guidelines["recommended_days"]

        reasonable = True

        if duration_days < min_days:
            reasonable = False
            warnings.append(f"Duration too short for {purpose} (minimum: {min_days} days)")
            suggestions.append(
                ComplianceSuggestion(
                    category=SuggestionCategory.DURATION,
                    title="Duration Too Short",
                    description=f"Consent duration is below minimum for {purpose}",
                    recommendation=f"Set duration to at least {min_days} days",
                    severity="warning",
                    dpdp_section="Section 7",
                    auto_fix={"duration_days": min_days},
                )
            )

        if duration_days > max_days:
            warnings.append(f"Duration exceeds recommended maximum for {purpose}")
            suggestions.append(
                ComplianceSuggestion(
                    category=SuggestionCategory.DURATION,
                    title="Duration Exceeds Maximum",
                    description=f"Consent duration exceeds recommended maximum for {purpose}",
                    recommendation=f"Consider reducing duration to {max_days} days or less",
                    severity="warning",
                    dpdp_section="Section 7",
                    auto_fix={"duration_days": max_days},
                )
            )

        if duration_days != recommended_days:
            suggestions.append(
                ComplianceSuggestion(
                    category=SuggestionCategory.DURATION,
                    title="Optimal Duration",
                    description=f"Recommended duration for {purpose} is {recommended_days} days",
                    recommendation=f"Consider setting duration to {recommended_days} days for optimal compliance",
                    severity="info",
                    auto_fix={"duration_days": recommended_days},
                )
            )

        return reasonable

    def _check_sensitive_data(
        self,
        data_types: List[str],
        purpose: str,
        suggestions: List[ComplianceSuggestion],
        warnings: List[str],
    ):
        for dt in data_types:
            if dt in self.sensitive_data:
                sensitive_info = self.sensitive_data[dt]
                restricted_purposes = sensitive_info.get("restricted_purposes", [])

                if purpose in restricted_purposes:
                    warnings.append(f"Sensitive data '{dt}' cannot be used for '{purpose}'")
                    suggestions.append(
                        ComplianceSuggestion(
                            category=SuggestionCategory.COMPLIANCE,
                            title="Sensitive Data Violation",
                            description=f"'{dt}' is sensitive and restricted for {purpose}",
                            recommendation="Change purpose or remove sensitive data type",
                            severity="critical",
                            dpdp_section="Section 4",
                        )
                    )

                recommended_duration = sensitive_info.get("recommended_duration_days", 90)
                suggestions.append(
                    ComplianceSuggestion(
                        category=SuggestionCategory.COMPLIANCE,
                        title="Sensitive Data Notice",
                        description=f"'{dt}' requires explicit consent (DPDP {sensitive_info.get('dpdp_note', '')})",
                        recommendation=f"Ensure explicit consent is obtained. Recommended max duration: {recommended_duration} days",
                        severity="warning",
                        dpdp_section="Section 4",
                    )
                )

    def _check_cross_border(
        self,
        cross_border: bool,
        suggestions: List[ComplianceSuggestion],
        warnings: List[str],
    ):
        if cross_border:
            warnings.append("Cross-border data transfer requires additional safeguards")
            suggestions.append(
                ComplianceSuggestion(
                    category=SuggestionCategory.COMPLIANCE,
                    title="Cross-Border Transfer",
                    description="Data will be transferred outside India",
                    recommendation="Ensure adequate data protection measures in receiving country per DPDP Section 12",
                    severity="warning",
                    dpdp_section="Section 12",
                )
            )

    def _check_dpdp_section(
        self,
        section: str,
        purpose: str,
        data_types: List[str],
        duration_days: int,
    ) -> bool:
        return True

    def _calculate_compliance_score(
        self,
        purpose_valid: bool,
        data_appropriate: bool,
        duration_reasonable: bool,
        suggestions: List[ComplianceSuggestion],
    ) -> float:
        base_score = 100.0

        if not purpose_valid:
            base_score -= 20
        if not data_appropriate:
            base_score -= 25
        if not duration_reasonable:
            base_score -= 10

        for suggestion in suggestions:
            if suggestion.severity == "critical":
                base_score -= 15
            elif suggestion.severity == "warning":
                base_score -= 5
            elif suggestion.severity == "info":
                base_score -= 1

        return max(0.0, min(100.0, base_score))

    def suggest_consent_terms(
        self,
        industry: Optional[str] = None,
        use_case: Optional[str] = None,
    ) -> Dict[str, Any]:
        suggestions: Dict[str, Any] = {
            "recommended_purposes": [],
            "recommended_data_types": [],
            "recommended_duration": 365,
            "suggested_templates": [],
        }

        if industry == "healthcare":
            suggestions["recommended_purposes"] = ["SERVICE_DELIVERY", "COMPLIANCE", "RESEARCH"]
            suggestions["recommended_data_types"] = ["personal_info", "contact_info", "health_data"]
            suggestions["recommended_duration"] = 730
            suggestions["suggested_templates"] = ["healthcare_consent", "research_consent"]

        elif industry == "finance":
            suggestions["recommended_purposes"] = [
                "SERVICE_DELIVERY",
                "PAYMENT_PROCESSING",
                "COMPLIANCE",
            ]
            suggestions["recommended_data_types"] = [
                "personal_info",
                "contact_info",
                "financial_data",
            ]
            suggestions["recommended_duration"] = 365
            suggestions["suggested_templates"] = ["financial_consent", "payment_consent"]

        elif industry == "ecommerce":
            suggestions["recommended_purposes"] = ["SERVICE_DELIVERY", "MARKETING", "ANALYTICS"]
            suggestions["recommended_data_types"] = [
                "personal_info",
                "contact_info",
                "location_data",
            ]
            suggestions["recommended_duration"] = 365
            suggestions["suggested_templates"] = ["marketing_consent", "service_delivery"]

        else:
            suggestions["recommended_purposes"] = ["SERVICE_DELIVERY"]
            suggestions["recommended_data_types"] = ["personal_info", "contact_info"]
            suggestions["recommended_duration"] = 365

        return suggestions

    def generate_compliance_checklist(self) -> List[Dict[str, str]]:
        return [
            {
                "item": "Consent is freely given",
                "description": "No pre-checked boxes or bundled consents",
                "dpdp_section": "Section 4",
                "status": "required",
            },
            {
                "item": "Purpose is clearly stated",
                "description": "Specific and unambiguous purpose for data processing",
                "dpdp_section": "Section 5",
                "status": "required",
            },
            {
                "item": "Data types are specified",
                "description": "Clear list of all data types being collected",
                "dpdp_section": "Section 6",
                "status": "required",
            },
            {
                "item": "Consent duration is reasonable",
                "description": "Duration appropriate for purpose",
                "dpdp_section": "Section 7",
                "status": "recommended",
            },
            {
                "item": "Withdrawal mechanism exists",
                "description": "Easy way for users to withdraw consent",
                "dpdp_section": "Section 8",
                "status": "required",
            },
            {
                "item": "Erasure request process",
                "description": "Process for handling deletion requests within 30 days",
                "dpdp_section": "Section 9",
                "status": "required",
            },
            {
                "item": "Data access provision",
                "description": "Users can access their personal data",
                "dpdp_section": "Section 10",
                "status": "required",
            },
            {
                "item": "Correction mechanism",
                "description": "Users can correct inaccurate data",
                "dpdp_section": "Section 11",
                "status": "required",
            },
            {
                "item": "Breach notification process",
                "description": "72-hour breach notification process",
                "dpdp_section": "Section 17",
                "status": "required",
            },
        ]


ai_assistant = AIComplianceAssistant()
