"""Tests for new features: WebSocket, i18n, AI Assistant, Analytics, WebAuthn, Mobile SDK."""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, AsyncMock
import json


class TestWebSocket:
    """Tests for WebSocket real-time updates."""

    def test_ws_message_creation(self):
        from api.websocket import WSMessage, WSMessageType

        msg = WSMessage(
            type=WSMessageType.CONSENT_GRANTED,
            data={"consent_id": "test-123"},
            principal_id="user-1",
        )

        json_str = msg.to_json()
        parsed = json.loads(json_str)

        assert parsed["type"] == "consent_granted"
        assert parsed["data"]["consent_id"] == "test-123"
        assert parsed["principal_id"] == "user-1"

    def test_connection_manager_stats(self):
        from api.websocket import ConnectionManager

        manager = ConnectionManager()
        stats = manager.get_connection_count()

        assert stats["total"] == 0
        assert stats["principals"] == 0
        assert stats["fiduciaries"] == 0


class TestI18N:
    """Tests for multi-language templates."""

    def test_get_supported_languages(self):
        from api.i18n import i18n_service, Language

        languages = i18n_service.get_supported_languages()

        assert len(languages) >= 4
        lang_codes = [l["code"] for l in languages]
        assert "en" in lang_codes
        assert "hi" in lang_codes
        assert "ta" in lang_codes
        assert "bn" in lang_codes

    def test_get_term_translation(self):
        from api.i18n import i18n_service, Language

        en_term = i18n_service.get_term_translation("personal_info", Language.ENGLISH)
        hi_term = i18n_service.get_term_translation("personal_info", Language.HINDI)
        ta_term = i18n_service.get_term_translation("personal_info", Language.TAMIL)
        bn_term = i18n_service.get_term_translation("personal_info", Language.BENGALI)

        assert en_term == "Personal Information"
        assert "व्यक्तिगत" in hi_term
        assert "தனிப்பட்ட" in ta_term
        assert "ব্যক্তিগত" in bn_term

    def test_render_template(self):
        from api.i18n import i18n_service, Language

        rendered = i18n_service.render_template(
            "marketing_consent",
            Language.ENGLISH,
            fiduciary_name="Test Company",
            data_types=["personal_info", "contact_info"],
            duration_days=365,
        )

        assert rendered is not None
        assert "Test Company" in rendered
        assert "365" in rendered

    def test_render_hindi_template(self):
        from api.i18n import i18n_service, Language

        rendered = i18n_service.render_template(
            "marketing_consent",
            Language.HINDI,
            fiduciary_name="Test Company",
            data_types=["personal_info"],
            duration_days=180,
        )

        assert rendered is not None
        assert "180" in rendered


class TestAIAssistant:
    """Tests for AI compliance assistant."""

    def test_analyze_consent_valid(self):
        from api.ai_assistant import ai_assistant

        analysis = ai_assistant.analyze_consent(
            purpose="MARKETING",
            data_types=["contact_info", "personal_info"],
            duration_days=180,
        )

        assert analysis.purpose_valid is True
        assert analysis.compliance_score >= 0
        assert isinstance(analysis.suggestions, list)

    def test_analyze_consent_sensitive_data_restriction(self):
        from api.ai_assistant import ai_assistant

        analysis = ai_assistant.analyze_consent(
            purpose="MARKETING",
            data_types=["health_data"],
            duration_days=365,
        )

        assert len(analysis.warnings) > 0
        has_critical = any(s.severity == "critical" for s in analysis.suggestions)
        assert has_critical

    def test_analyze_duration_recommendations(self):
        from api.ai_assistant import ai_assistant

        analysis = ai_assistant.analyze_consent(
            purpose="MARKETING",
            data_types=["contact_info"],
            duration_days=500,
        )

        has_duration_suggestion = any(s.category.value == "duration" for s in analysis.suggestions)
        assert has_duration_suggestion

    def test_suggest_consent_terms_healthcare(self):
        from api.ai_assistant import ai_assistant

        suggestions = ai_assistant.suggest_consent_terms(industry="healthcare")

        assert "SERVICE_DELIVERY" in suggestions["recommended_purposes"]
        assert "health_data" in suggestions["recommended_data_types"]

    def test_generate_compliance_checklist(self):
        from api.ai_assistant import ai_assistant

        checklist = ai_assistant.generate_compliance_checklist()

        assert len(checklist) >= 9
        items = [c["item"] for c in checklist]
        assert "Consent is freely given" in items
        assert "Withdrawal mechanism exists" in items


class TestAnalytics:
    """Tests for analytics engine."""

    def test_calculate_consent_metrics(self):
        from api.analytics import analytics_engine
        from datetime import datetime, timezone, timedelta

        now = datetime.now(timezone.utc)
        consents = [
            {"status": "GRANTED", "created_at": now - timedelta(days=5)},
            {"status": "GRANTED", "created_at": now - timedelta(days=10)},
            {"status": "REVOKED", "created_at": now - timedelta(days=15)},
            {"status": "EXPIRED", "created_at": now - timedelta(days=20)},
        ]

        metrics = analytics_engine.calculate_consent_metrics(consents, period_days=30)

        assert "total_consents" in metrics
        assert metrics["total_consents"].current_value == 4

    def test_predict_expiring_consents(self):
        from api.analytics import analytics_engine
        from datetime import datetime, timezone, timedelta

        now = datetime.now(timezone.utc)
        consents = [
            {
                "consent_id": "c1",
                "principal_id": "p1",
                "purpose": "MARKETING",
                "status": "GRANTED",
                "expires_at": now + timedelta(days=5),
            },
            {
                "consent_id": "c2",
                "principal_id": "p2",
                "purpose": "SERVICE_DELIVERY",
                "status": "GRANTED",
                "expires_at": now + timedelta(days=25),
            },
        ]

        predictions = analytics_engine.predict_expiring_consents(consents, days_ahead=30)

        assert len(predictions) >= 1
        assert predictions[0].days_remaining <= 30

    def test_calculate_trends(self):
        from api.analytics import analytics_engine
        from datetime import datetime, timezone, timedelta

        now = datetime.now(timezone.utc)
        consents = [
            {"status": "GRANTED", "created_at": now - timedelta(days=10)},
            {"status": "REVOKED", "created_at": now - timedelta(days=20)},
        ]

        trends = analytics_engine.calculate_trends(consents, periods=3, period_days=30)

        assert len(trends) == 3


class TestWebAuthn:
    """Tests for WebAuthn authentication."""

    def test_generate_challenge(self):
        from api.webauthn import webauthn_service

        challenge1 = webauthn_service.generate_challenge()
        challenge2 = webauthn_service.generate_challenge()

        assert len(challenge1) > 20
        assert challenge1 != challenge2

    def test_create_registration_options(self):
        from api.webauthn import webauthn_service, WebAuthnUser

        user = WebAuthnUser(
            user_id="user-123",
            username="testuser",
            display_name="Test User",
        )

        options = webauthn_service.create_registration_options(user)

        assert options.challenge is not None
        assert options.rp["id"] == webauthn_service.rp_id
        assert options.timeout == 60000

    def test_create_authentication_options(self):
        from api.webauthn import webauthn_service

        options = webauthn_service.create_authentication_options(user_id="user-123")

        assert options.challenge is not None
        assert options.rpId == webauthn_service.rp_id

    def test_verify_challenge(self):
        from api.webauthn import webauthn_service

        challenge = webauthn_service.generate_challenge()
        webauthn_service.store_challenge("user-123", challenge)

        assert webauthn_service.verify_challenge("user-123", challenge) is True
        assert webauthn_service.verify_challenge("user-123", "wrong") is False


class TestMobileSDK:
    """Tests for Mobile SDK support."""

    def test_register_device(self):
        from api.mobile import mobile_sdk_support, MobileDevice, MobilePlatform

        device = MobileDevice(
            device_id="device-123",
            platform=MobilePlatform.IOS,
            push_token="abc123",
            app_version="1.0.0",
        )

        result = mobile_sdk_support.register_device("user-123", device)

        assert result["success"] is True
        assert result["device_id"] == "device-123"

    def test_unregister_device(self):
        from api.mobile import mobile_sdk_support, MobileDevice, MobilePlatform

        device = MobileDevice(
            device_id="device-456",
            platform=MobilePlatform.ANDROID,
        )
        mobile_sdk_support.register_device("user-456", device)

        success = mobile_sdk_support.unregister_device("device-456")

        assert success is True

    def test_generate_deep_link(self):
        from api.mobile import mobile_sdk_support

        link = mobile_sdk_support.generate_deep_link(
            path="consent/view",
            params={"id": "123"},
            source="email",
        )

        assert "consentchain://" in link
        assert "consent/view" in link

    def test_parse_deep_link(self):
        from api.mobile import mobile_sdk_support

        link = "consentchain://consent/view?id=123&source=email"
        parsed = mobile_sdk_support.parse_deep_link(link)

        assert parsed is not None
        assert parsed.path == "consent/view"
        assert parsed.params.get("id") == "123"

    def test_get_user_devices(self):
        from api.mobile import mobile_sdk_support, MobileDevice, MobilePlatform

        device = MobileDevice(
            device_id="device-789",
            platform=MobilePlatform.REACT_NATIVE,
        )
        mobile_sdk_support.register_device("user-789", device)

        devices = mobile_sdk_support.get_user_devices("user-789")

        assert len(devices) >= 1
        assert any(d.device_id == "device-789" for d in devices)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
