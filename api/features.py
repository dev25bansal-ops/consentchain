from fastapi import APIRouter, HTTPException, Depends, Query, WebSocket, WebSocketDisconnect
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

from api.websocket import (
    manager as ws_manager,
    ws_handler,
    WSMessageType,
    WSMessage,
    notify_consent_granted,
    notify_consent_revoked,
    notify_consent_modified,
    notify_consent_expiring,
    notify_breach,
    notify_deletion_request,
)
from api.i18n import i18n_service, Language, ConsentTemplate
from api.ai_assistant import ai_assistant, ConsentAnalysis, ComplianceSuggestion
from api.analytics import analytics_engine, DashboardData, ExpiryPrediction
from api.webauthn import (
    webauthn_service,
    WebAuthnUser,
    CredentialCreationOptions,
    CredentialRequestOptions,
    RegistrationResult,
    AuthenticationResult,
)
from api.mobile import (
    mobile_sdk_support,
    MobileDevice,
    MobilePlatform,
    PushNotification,
    NotificationType,
    SDK_DOCUMENTATION,
)


router = APIRouter(prefix="/api/v1/realtime", tags=["WebSocket"])


# ============ WebSocket Endpoints ============


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    principal_id: Optional[str] = Query(None),
    fiduciary_id: Optional[str] = Query(None),
    is_admin: bool = Query(False),
):
    """WebSocket endpoint for real-time consent updates."""
    await ws_handler.listen(websocket, principal_id, fiduciary_id, is_admin)


@router.get("/connections")
async def get_connection_stats():
    """Get WebSocket connection statistics."""
    return ws_manager.get_connection_count()


# ============ I18N Endpoints ============

i18n_router = APIRouter(prefix="/api/v1/i18n", tags=["Internationalization"])


class TemplateRenderRequest(BaseModel):
    template_id: str
    language: str = "en"
    fiduciary_name: str = ""
    data_types: List[str] = []
    duration_days: int = 365


@i18n_router.get("/languages")
async def get_supported_languages():
    """Get list of supported languages."""
    return {"languages": i18n_service.get_supported_languages()}


@i18n_router.get("/templates")
async def get_available_templates():
    """Get list of available consent templates."""
    return {"templates": i18n_service.get_available_templates()}


@i18n_router.get("/templates/{template_id}")
async def get_template(
    template_id: str,
    language: str = Query("en"),
):
    """Get a consent template in the specified language."""
    try:
        lang = Language(language)
    except ValueError:
        lang = Language.ENGLISH

    template = i18n_service.get_template(template_id, lang)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    return {
        "template_id": template.template_id,
        "category": template.category,
        "language": template.language.value,
        "title": template.title,
        "summary": template.summary,
        "terms": template.terms,
        "data_types": template.data_types,
        "purpose": template.purpose,
        "duration_days": template.duration_days,
    }


@i18n_router.post("/templates/render")
async def render_template(request: TemplateRenderRequest):
    """Render a consent template with provided values."""
    try:
        lang = Language(request.language)
    except ValueError:
        lang = Language.ENGLISH

    rendered = i18n_service.render_template(
        request.template_id,
        lang,
        request.fiduciary_name,
        request.data_types,
        request.duration_days,
    )

    if not rendered:
        raise HTTPException(status_code=404, detail="Template not found")

    return {"rendered_text": rendered}


@i18n_router.get("/terms/{term_id}")
async def get_term(
    term_id: str,
    language: str = Query("en"),
):
    """Get a consent term with translations."""
    try:
        lang = Language(language)
    except ValueError:
        lang = Language.ENGLISH

    term = i18n_service.get_term(term_id)
    if not term:
        raise HTTPException(status_code=404, detail="Term not found")

    return {
        "term_id": term.term_id,
        "translation": term.translations.get(lang.value, term.translations.get("en")),
        "description": term.description.get(lang.value, term.description.get("en")),
    }


# ============ AI Assistant Endpoints ============

ai_router = APIRouter(prefix="/api/v1/ai", tags=["AI Assistant"])


class ConsentAnalysisRequest(BaseModel):
    purpose: str
    data_types: List[str]
    duration_days: int
    fiduciary_type: Optional[str] = None
    cross_border: bool = False


class IndustrySuggestionRequest(BaseModel):
    industry: Optional[str] = None
    use_case: Optional[str] = None


@ai_router.post("/analyze", response_model=ConsentAnalysis)
async def analyze_consent(request: ConsentAnalysisRequest):
    """Analyze a consent request for DPDP compliance."""
    return ai_assistant.analyze_consent(
        purpose=request.purpose,
        data_types=request.data_types,
        duration_days=request.duration_days,
        fiduciary_type=request.fiduciary_type,
        cross_border=request.cross_border,
    )


@ai_router.post("/suggest")
async def suggest_consent_terms(request: IndustrySuggestionRequest):
    """Get AI-suggested consent terms based on industry."""
    return ai_assistant.suggest_consent_terms(
        industry=request.industry,
        use_case=request.use_case,
    )


@ai_router.get("/checklist")
async def get_compliance_checklist():
    """Get DPDP compliance checklist."""
    return {"checklist": ai_assistant.generate_compliance_checklist()}


# ============ Analytics Endpoints ============

analytics_router = APIRouter(prefix="/api/v1/analytics", tags=["Analytics"])


class MockConsentData(BaseModel):
    consents: List[Dict[str, Any]]


@analytics_router.post("/metrics")
async def calculate_metrics(
    consents: MockConsentData,
    period_days: int = Query(30, ge=1, le=365),
):
    """Calculate consent metrics for a period."""
    metrics = analytics_engine.calculate_consent_metrics(
        consents.consents,
        period_days,
    )
    return {
        k: {
            "current_value": v.current_value,
            "previous_value": v.previous_value,
            "change_percent": v.change_percent,
            "trend": v.trend,
        }
        for k, v in metrics.items()
    }


@analytics_router.post("/dashboard", response_model=DashboardData)
async def generate_dashboard(
    consents: MockConsentData,
    include_predictions: bool = Query(True),
):
    """Generate analytics dashboard data."""
    return analytics_engine.generate_dashboard(
        consents.consents,
        include_predictions,
    )


@analytics_router.post("/expiring")
async def predict_expiring(
    consents: MockConsentData,
    days_ahead: int = Query(30, ge=1, le=90),
):
    """Predict consents expiring within a period."""
    predictions = analytics_engine.predict_expiring_consents(
        consents.consents,
        days_ahead,
    )
    return {
        "predictions": [
            {
                "consent_id": p.consent_id,
                "principal_id": p.principal_id,
                "purpose": p.purpose,
                "expires_at": p.expires_at.isoformat(),
                "days_remaining": p.days_remaining,
                "renewal_probability": p.renewal_probability,
                "suggested_action": p.suggested_action,
            }
            for p in predictions
        ]
    }


@analytics_router.post("/trends")
async def calculate_trends(
    consents: MockConsentData,
    periods: int = Query(6, ge=1, le=12),
    period_days: int = Query(30, ge=7, le=90),
):
    """Calculate consent trends over multiple periods."""
    trends = analytics_engine.calculate_trends(
        consents.consents,
        periods,
        period_days,
    )
    return {"trends": trends}


# ============ WebAuthn Endpoints ============

webauthn_router = APIRouter(prefix="/api/v1/webauthn", tags=["WebAuthn"])


class WebAuthnUserCreate(BaseModel):
    user_id: str
    username: str
    display_name: str


class WebAuthnRegistrationRequest(BaseModel):
    user_id: str
    credential: Dict[str, Any]
    client_data: Dict[str, Any]


class WebAuthnAuthenticationRequest(BaseModel):
    credential: Dict[str, Any]
    client_data: Dict[str, Any]


@webauthn_router.post("/register/start")
async def start_registration(user: WebAuthnUserCreate):
    """Start WebAuthn registration process."""
    webauthn_user = WebAuthnUser(
        user_id=user.user_id,
        username=user.username,
        display_name=user.display_name,
    )
    webauthn_service.register_user(webauthn_user)

    options = webauthn_service.create_registration_options(webauthn_user)

    return {
        "challenge": options.challenge,
        "rp": options.rp,
        "user": options.user,
        "pubKeyCredParams": options.pubKeyCredParams,
        "timeout": options.timeout,
        "attestation": options.attestation,
        "authenticatorSelection": options.authenticatorSelection,
        "excludeCredentials": options.excludeCredentials,
    }


@webauthn_router.post("/register/finish", response_model=RegistrationResult)
async def finish_registration(request: WebAuthnRegistrationRequest):
    """Finish WebAuthn registration process."""
    return webauthn_service.verify_registration(
        request.user_id,
        request.credential,
        request.client_data,
    )


@webauthn_router.post("/authenticate/start")
async def start_authentication(
    user_id: Optional[str] = None,
    credential_ids: Optional[List[str]] = None,
):
    """Start WebAuthn authentication process."""
    options = webauthn_service.create_authentication_options(
        user_id=user_id,
        credential_ids=credential_ids,
    )

    return {
        "challenge": options.challenge,
        "timeout": options.timeout,
        "rpId": options.rpId,
        "allowCredentials": options.allowCredentials,
        "userVerification": options.userVerification,
    }


@webauthn_router.post("/authenticate/finish", response_model=AuthenticationResult)
async def finish_authentication(request: WebAuthnAuthenticationRequest):
    """Finish WebAuthn authentication process."""
    return webauthn_service.verify_authentication(
        request.credential,
        request.client_data,
    )


@webauthn_router.delete("/credentials/{credential_id}")
async def remove_credential(credential_id: str):
    """Remove a WebAuthn credential."""
    success = webauthn_service.remove_credential(credential_id)
    if not success:
        raise HTTPException(status_code=404, detail="Credential not found")
    return {"success": True}


# ============ Mobile SDK Endpoints ============

mobile_router = APIRouter(prefix="/api/v1/mobile", tags=["Mobile SDK"])


class DeviceRegisterRequest(BaseModel):
    user_id: str
    device_id: str
    platform: str
    push_token: Optional[str] = None
    app_version: Optional[str] = None
    os_version: Optional[str] = None
    notification_enabled: bool = True
    biometric_enabled: bool = False


class PushNotificationRequest(BaseModel):
    user_id: str
    title: str
    body: str
    notification_type: str
    data: Dict[str, Any] = {}
    devices: Optional[List[str]] = None


@mobile_router.post("/devices/register")
async def register_device(request: DeviceRegisterRequest):
    """Register a mobile device."""
    try:
        platform = MobilePlatform(request.platform)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid platform")

    device = MobileDevice(
        device_id=request.device_id,
        platform=platform,
        push_token=request.push_token,
        app_version=request.app_version,
        os_version=request.os_version,
        notification_enabled=request.notification_enabled,
        biometric_enabled=request.biometric_enabled,
    )

    return mobile_sdk_support.register_device(request.user_id, device)


@mobile_router.delete("/devices/{device_id}")
async def unregister_device(device_id: str):
    """Unregister a mobile device."""
    success = mobile_sdk_support.unregister_device(device_id)
    if not success:
        raise HTTPException(status_code=404, detail="Device not found")
    return {"success": True}


@mobile_router.put("/devices/{device_id}/push-token")
async def update_push_token(device_id: str, push_token: str):
    """Update push notification token for a device."""
    success = mobile_sdk_support.update_push_token(device_id, push_token)
    if not success:
        raise HTTPException(status_code=404, detail="Device not found")
    return {"success": True}


@mobile_router.post("/notifications/send")
async def send_notification(request: PushNotificationRequest):
    """Send push notification to user's devices."""
    try:
        notification_type = NotificationType(request.notification_type)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid notification type")

    notification = PushNotification(
        title=request.title,
        body=request.body,
        notification_type=notification_type,
        data=request.data,
    )

    result = await mobile_sdk_support.send_push_notification(
        request.user_id,
        notification,
        request.devices,
    )
    return result


@mobile_router.get("/devices/user/{user_id}")
async def get_user_devices(user_id: str):
    """Get all devices for a user."""
    devices = mobile_sdk_support.get_user_devices(user_id)
    return {
        "devices": [
            {
                "device_id": d.device_id,
                "platform": d.platform.value,
                "app_version": d.app_version,
                "last_active": d.last_active.isoformat(),
                "notification_enabled": d.notification_enabled,
                "biometric_enabled": d.biometric_enabled,
            }
            for d in devices
        ]
    }


@mobile_router.get("/deep-link")
async def generate_deep_link(
    path: str,
    params: Optional[str] = None,
    source: Optional[str] = None,
):
    """Generate a deep link for mobile app."""
    param_dict = {}
    if params:
        for pair in params.split(","):
            if "=" in pair:
                k, v = pair.split("=", 1)
                param_dict[k] = v

    link = mobile_sdk_support.generate_deep_link(path, param_dict, source)
    return {"deep_link": link}


@mobile_router.get("/sdk-docs/{platform}")
async def get_sdk_documentation(platform: str):
    """Get SDK documentation for a platform."""
    if platform not in SDK_DOCUMENTATION:
        raise HTTPException(status_code=404, detail="Platform not found")

    return {"platform": platform, "documentation": SDK_DOCUMENTATION[platform]}
