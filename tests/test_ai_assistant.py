"""Tests for AI Compliance Assistant.

Covers:
- Consent analysis (valid and invalid scenarios)
- Sensitive data detection
- Duration validation
- Cross-border transfer checks
- Compliance scoring
- Industry-specific suggestions
- Compliance checklist generation
"""

import pytest
from api.ai_assistant import (
    ai_assistant,
    AIComplianceAssistant,
    ComplianceSuggestion,
    ConsentAnalysis,
    SuggestionCategory,
    DPDP_PROVISIONS,
    SENSITIVE_DATA_TYPES,
    PURPOSE_DURATIONS,
)


# ============================================================
# Test: Consent Analysis - Valid Scenarios
# ============================================================


class TestValidConsentAnalysis:
    """Test analysis of valid consent configurations."""

    def test_marketing_consent_valid(self):
        """Standard marketing consent passes analysis."""
        analysis = ai_assistant.analyze_consent(
            purpose="MARKETING",
            data_types=["contact_info", "personal_info"],
            duration_days=180,
        )

        assert analysis.purpose_valid is True
        assert analysis.data_types_appropriate is True
        assert 0 <= analysis.compliance_score <= 100

    def test_service_delivery_consent_valid(self):
        """Service delivery consent with appropriate data types."""
        analysis = ai_assistant.analyze_consent(
            purpose="SERVICE_DELIVERY",
            data_types=["personal_info", "contact_info", "financial_data"],
            duration_days=365,
        )

        assert analysis.purpose_valid is True
        assert analysis.data_types_appropriate is True

    def test_compliance_consent_long_duration(self):
        """Compliance purpose allows longer duration."""
        analysis = ai_assistant.analyze_consent(
            purpose="COMPLIANCE",
            data_types=["personal_info", "financial_data"],
            duration_days=2555,
        )

        assert analysis.purpose_valid is True
        assert analysis.duration_reasonable is True

    def test_payment_processing_consent(self):
        """Payment processing consent analysis."""
        analysis = ai_assistant.analyze_consent(
            purpose="PAYMENT_PROCESSING",
            data_types=["financial_data", "personal_info"],
            duration_days=365,
        )

        assert analysis.purpose_valid is True
        assert analysis.data_types_appropriate is True


# ============================================================
# Test: Consent Analysis - Invalid Scenarios
# ============================================================


class TestInvalidConsentAnalysis:
    """Test analysis of invalid consent configurations."""

    def test_nonstandard_purpose(self):
        """Non-standard purpose generates warning."""
        analysis = ai_assistant.analyze_consent(
            purpose="CUSTOM_PURPOSE",
            data_types=["personal_info"],
            duration_days=365,
        )

        assert analysis.purpose_valid is False
        assert any("non-standard" in w.lower() or "not a standard" in w.lower() for w in analysis.warnings)

    def test_sensitive_data_for_marketing(self):
        """Health data restricted for marketing purpose."""
        analysis = ai_assistant.analyze_consent(
            purpose="MARKETING",
            data_types=["health_data"],
            duration_days=180,
        )

        assert analysis.data_types_appropriate is False
        has_critical = any(s.severity == "critical" for s in analysis.suggestions)
        assert has_critical

    def test_biometric_data_for_marketing(self):
        """Biometric data restricted for marketing."""
        analysis = ai_assistant.analyze_consent(
            purpose="MARKETING",
            data_types=["biometric_data"],
            duration_days=90,
        )

        assert analysis.data_types_appropriate is False
        has_critical = any(s.severity == "critical" for s in analysis.suggestions)
        assert has_critical

    def test_no_data_types(self):
        """Empty data types list generates warning."""
        analysis = ai_assistant.analyze_consent(
            purpose="MARKETING",
            data_types=[],
            duration_days=180,
        )

        assert analysis.data_types_appropriate is False
        assert any("no data types" in w.lower() for w in analysis.warnings)

    def test_duration_too_short(self):
        """Duration below minimum generates warning."""
        analysis = ai_assistant.analyze_consent(
            purpose="RESEARCH",
            data_types=["personal_info"],
            duration_days=10,  # Min is 90
        )

        assert analysis.duration_reasonable is False
        has_duration_warning = any(
            s.category == SuggestionCategory.DURATION and "short" in s.title.lower()
            for s in analysis.suggestions
        )
        assert has_duration_warning

    def test_duration_exceeds_maximum(self):
        """Duration above maximum generates warning."""
        analysis = ai_assistant.analyze_consent(
            purpose="MARKETING",
            data_types=["contact_info"],
            duration_days=500,  # Max is 365
        )

        has_max_warning = any(
            s.category == SuggestionCategory.DURATION and "exceeds" in s.title.lower()
            for s in analysis.suggestions
        )
        assert has_max_warning


# ============================================================
# Test: Sensitive Data Checks
# ============================================================


class TestSensitiveDataChecks:
    """Test sensitive data type handling."""

    def test_health_data_requires_explicit_consent(self):
        """Health data flagged as requiring explicit consent."""
        analysis = ai_assistant.analyze_consent(
            purpose="RESEARCH",
            data_types=["health_data"],
            duration_days=365,
        )

        has_sensitive_notice = any(
            "sensitive" in s.title.lower() or "sensitive" in s.description.lower()
            for s in analysis.suggestions
        )
        assert has_sensitive_notice

    def test_financial_data_for_third_party_sharing(self):
        """Financial data allowed for third party sharing with consent."""
        analysis = ai_assistant.analyze_consent(
            purpose="THIRD_PARTY_SHARING",
            data_types=["financial_data"],
            duration_days=90,
        )

        # Financial data is allowed (not restricted) for third party sharing
        assert analysis.data_types_appropriate is True

    def test_location_data_for_marketing(self):
        """Location data allowed but flagged for marketing."""
        analysis = ai_assistant.analyze_consent(
            purpose="MARKETING",
            data_types=["location_data"],
            duration_days=90,
        )

        # Location data is allowed for marketing
        assert analysis.data_types_appropriate is True

    def test_sensitive_data_all_types_listed(self):
        """All sensitive data types are defined."""
        assert "health_data" in SENSITIVE_DATA_TYPES
        assert "biometric_data" in SENSITIVE_DATA_TYPES
        assert "financial_data" in SENSITIVE_DATA_TYPES
        assert "location_data" in SENSITIVE_DATA_TYPES

        for dt, info in SENSITIVE_DATA_TYPES.items():
            assert "requires_explicit_consent" in info
            assert "restricted_purposes" in info
            assert "recommended_duration_days" in info


# ============================================================
# Test: Cross-Border Transfer Checks
# ============================================================


class TestCrossBorderChecks:
    """Test cross-border data transfer analysis."""

    def test_cross_border_transfer_flagged(self):
        """Cross-border transfer generates warning."""
        analysis = ai_assistant.analyze_consent(
            purpose="SERVICE_DELIVERY",
            data_types=["personal_info"],
            duration_days=365,
            cross_border=True,
        )

        assert any("cross-border" in w.lower() or "transfer" in w.lower() for w in analysis.warnings)
        has_cross_border_suggestion = any(
            s.dpdp_section == "Section 12" for s in analysis.suggestions
        )
        assert has_cross_border_suggestion

    def test_no_cross_border_no_warning(self):
        """No cross-border transfer: no related warning."""
        analysis = ai_assistant.analyze_consent(
            purpose="SERVICE_DELIVERY",
            data_types=["personal_info"],
            duration_days=365,
            cross_border=False,
        )

        has_cross_border_warning = any(
            "cross-border" in w.lower() or "transfer" in w.lower()
            for w in analysis.warnings
        )
        assert not has_cross_border_warning


# ============================================================
# Test: Compliance Scoring
# ============================================================


class TestComplianceScoring:
    """Test compliance score calculation."""

    def test_perfect_score_range(self):
        """Score is within valid range."""
        analysis = ai_assistant.analyze_consent(
            purpose="MARKETING",
            data_types=["contact_info", "personal_info"],
            duration_days=180,
        )
        assert 0 <= analysis.compliance_score <= 100

    def test_critical_violations_lower_score(self):
        """Critical violations significantly reduce score."""
        analysis = ai_assistant.analyze_consent(
            purpose="MARKETING",
            data_types=["health_data", "biometric_data"],
            duration_days=500,
        )

        # Multiple critical violations should produce low score
        assert analysis.compliance_score < 50

    def test_score_with_warnings_only(self):
        """Warning-only violations produce moderate score."""
        analysis = ai_assistant.analyze_consent(
            purpose="MARKETING",
            data_types=["contact_info"],
            duration_days=500,  # Exceeds max
        )

        assert analysis.compliance_score < 100
        assert analysis.compliance_score > 0

    def test_dpdp_compliance_mapping(self):
        """DPDP compliance map has all sections."""
        analysis = ai_assistant.analyze_consent(
            purpose="SERVICE_DELIVERY",
            data_types=["personal_info"],
            duration_days=365,
        )

        for section in DPDP_PROVISIONS:
            assert section in analysis.dpdp_compliance


# ============================================================
# Test: Industry-Specific Suggestions
# ============================================================


class TestIndustrySuggestions:
    """Test industry-specific consent term suggestions."""

    def test_healthcare_suggestions(self):
        """Healthcare industry has appropriate suggestions."""
        suggestions = ai_assistant.suggest_consent_terms(industry="healthcare")

        assert "SERVICE_DELIVERY" in suggestions["recommended_purposes"]
        assert "health_data" in suggestions["recommended_data_types"]
        assert "healthcare_consent" in suggestions["suggested_templates"]

    def test_finance_suggestions(self):
        """Finance industry has appropriate suggestions."""
        suggestions = ai_assistant.suggest_consent_terms(industry="finance")

        assert "PAYMENT_PROCESSING" in suggestions["recommended_purposes"]
        assert "financial_data" in suggestions["recommended_data_types"]
        assert "financial_consent" in suggestions["suggested_templates"]

    def test_ecommerce_suggestions(self):
        """Ecommerce industry has appropriate suggestions."""
        suggestions = ai_assistant.suggest_consent_terms(industry="ecommerce")

        assert "MARKETING" in suggestions["recommended_purposes"]
        assert "location_data" in suggestions["recommended_data_types"]

    def test_default_suggestions(self):
        """No industry specified gives default suggestions."""
        suggestions = ai_assistant.suggest_consent_terms()

        assert suggestions["recommended_purposes"] == ["SERVICE_DELIVERY"]
        assert "personal_info" in suggestions["recommended_data_types"]
        assert suggestions["recommended_duration"] == 365


# ============================================================
# Test: Compliance Checklist
# ============================================================


class TestComplianceChecklist:
    """Test compliance checklist generation."""

    def test_checklist_has_required_items(self):
        """Checklist contains all required DPDP items."""
        checklist = ai_assistant.generate_compliance_checklist()

        assert len(checklist) >= 9

        items = [c["item"] for c in checklist]
        assert "Consent is freely given" in items
        assert "Purpose is clearly stated" in items
        assert "Data types are specified" in items
        assert "Withdrawal mechanism exists" in items
        assert "Erasure request process" in items

    def test_checklist_items_have_required_fields(self):
        """Each checklist item has required fields."""
        checklist = ai_assistant.generate_compliance_checklist()

        for item in checklist:
            assert "item" in item
            assert "description" in item
            assert "dpdp_section" in item
            assert "status" in item
            assert item["status"] in ("required", "recommended")

    def test_checklist_dpdp_sections(self):
        """Checklist references correct DPDP sections."""
        checklist = ai_assistant.generate_compliance_checklist()
        sections = [c["dpdp_section"] for c in checklist]

        assert "Section 4" in sections  # Free consent
        assert "Section 5" in sections  # Purpose
        assert "Section 6" in sections  # Data types
        assert "Section 8" in sections  # Withdrawal


# ============================================================
# Test: ComplianceSuggestion Dataclass
# ============================================================


class TestComplianceSuggestionModel:
    """Test ComplianceSuggestion dataclass."""

    def test_suggestion_creation(self):
        """Suggestion can be created with all fields."""
        suggestion = ComplianceSuggestion(
            category=SuggestionCategory.DURATION,
            title="Test Title",
            description="Test description",
            recommendation="Test recommendation",
            severity="warning",
            dpdp_section="Section 7",
            best_practice="Follow DPDP guidelines",
            auto_fix={"duration_days": 180},
        )

        assert suggestion.category == SuggestionCategory.DURATION
        assert suggestion.severity == "warning"
        assert suggestion.auto_fix == {"duration_days": 180}

    def test_severity_levels(self):
        """All severity levels are valid."""
        for severity in ["info", "warning", "critical"]:
            suggestion = ComplianceSuggestion(
                category=SuggestionCategory.PURPOSE,
                title="Test",
                description="Test",
                recommendation="Test",
                severity=severity,
            )
            assert suggestion.severity == severity
