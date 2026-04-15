"""Notification Service - User notifications for ConsentChain.

Supports:
- In-app notifications (database-stored)
- Email notifications via SendGrid
- SMS notifications via Twilio
"""

from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4
from enum import Enum
from dataclasses import dataclass, field
import json
import logging
import os
import asyncio

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, update

import httpx

logger = logging.getLogger(__name__)


class NotificationType(str, Enum):
    CONSENT_GRANTED = "CONSENT_GRANTED"
    CONSENT_EXPIRING = "CONSENT_EXPIRING"
    CONSENT_EXPIRED = "CONSENT_EXPIRED"
    CONSENT_REVOKED = "CONSENT_REVOKED"
    CONSENT_MODIFIED = "CONSENT_MODIFIED"
    GRIEVANCE_SUBMITTED = "GRIEVANCE_SUBMITTED"
    GRIEVANCE_ACKNOWLEDGED = "GRIEVANCE_ACKNOWLEDGED"
    GRIEVANCE_RESOLVED = "GRIEVANCE_RESOLVED"
    DELETION_REQUESTED = "DELETION_REQUESTED"
    DELETION_COMPLETED = "DELETION_COMPLETED"
    BREACH_NOTIFICATION = "BREACH_NOTIFICATION"
    GUARDIAN_REGISTERED = "GUARDIAN_REGISTERED"
    GUARDIAN_VERIFIED = "GUARDIAN_VERIFIED"
    SYSTEM_ANNOUNCEMENT = "SYSTEM_ANNOUNCEMENT"


@dataclass
class EmailNotification:
    recipient_email: str
    recipient_name: Optional[str] = None
    subject: str = ""
    html_body: str = ""
    text_body: Optional[str] = None
    template_id: Optional[str] = None
    template_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SMSNotification:
    recipient_phone: str
    message: str


@dataclass
class NotificationResult:
    success: bool
    notification_id: Optional[str] = None
    error: Optional[str] = None


class EmailProvider:
    def __init__(self):
        self.api_key = os.getenv("SENDGRID_API_KEY")
        self.from_email = os.getenv("SENDGRID_FROM_EMAIL", "noreply@consentchain.io")
        self.from_name = os.getenv("SENDGRID_FROM_NAME", "ConsentChain")
        self.base_url = "https://api.sendgrid.com/v3/mail/send"

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def send(self, notification: EmailNotification) -> NotificationResult:
        if not self.is_configured:
            logger.debug("SendGrid not configured, skipping email")
            return NotificationResult(success=False, error="SendGrid not configured")

        payload = {
            "personalizations": [
                {
                    "to": [{"email": notification.recipient_email}],
                    "subject": notification.subject,
                }
            ],
            "from": {"email": self.from_email, "name": self.from_name},
            "content": [{"type": "text/html", "value": notification.html_body}],
        }

        if notification.template_id:
            payload["template_id"] = notification.template_id
            payload["personalizations"][0]["dynamic_template_data"] = notification.template_data

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.base_url,
                    json=payload,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=30.0,
                )

            if response.status_code == 202:
                return NotificationResult(
                    success=True, notification_id=response.headers.get("X-Message-Id")
                )
            return NotificationResult(
                success=False, error=f"SendGrid error: {response.status_code}"
            )
        except Exception as e:
            logger.error(f"Email send failed: {e}")
            return NotificationResult(success=False, error=str(e))


class SMSProvider:
    def __init__(self):
        self.account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        self.auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        self.phone_number = os.getenv("TWILIO_PHONE_NUMBER")

    @property
    def is_configured(self) -> bool:
        return bool(self.account_sid and self.auth_token and self.phone_number)

    async def send(self, notification: SMSNotification) -> NotificationResult:
        if not self.is_configured:
            logger.debug("Twilio not configured, skipping SMS")
            return NotificationResult(success=False, error="Twilio not configured")

        url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Messages.json"

        phone = notification.recipient_phone
        if not phone.startswith("+"):
            phone = "+" + phone

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    data={
                        "From": self.phone_number,
                        "To": phone,
                        "Body": f"[ConsentChain] {notification.message}",
                    },
                    auth=(self.account_sid, self.auth_token),
                    timeout=30.0,
                )

            if response.status_code == 201:
                return NotificationResult(success=True, notification_id=response.json().get("sid"))
            return NotificationResult(success=False, error=f"Twilio error: {response.status_code}")
        except Exception as e:
            logger.error(f"SMS send failed: {e}")
            return NotificationResult(success=False, error=str(e))


class NotificationService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.email_provider = EmailProvider()
        self.sms_provider = SMSProvider()

    async def create_notification(
        self,
        principal_id: UUID,
        notification_type: NotificationType,
        title: str,
        message: str,
        action_url: Optional[str] = None,
        extra_data: Optional[Dict[str, Any]] = None,
    ) -> UUID:
        from api.database import NotificationDB

        notification_id = uuid4()
        notification = NotificationDB(
            id=notification_id,
            principal_id=principal_id,
            notification_type=notification_type.value,
            title=title,
            message=message,
            action_url=action_url,
            extra_data=json.dumps(extra_data) if extra_data else None,
            created_at=datetime.now(timezone.utc),
        )
        self.db.add(notification)
        await self.db.commit()

        logger.info(f"Created notification {notification_id} for principal {principal_id}")
        return notification_id

    async def send_email(
        self,
        recipient_email: str,
        subject: str,
        html_body: str,
        recipient_name: Optional[str] = None,
    ) -> NotificationResult:
        notification = EmailNotification(
            recipient_email=recipient_email,
            recipient_name=recipient_name,
            subject=subject,
            html_body=html_body,
        )
        return await self.email_provider.send(notification)

    async def send_sms(
        self,
        recipient_phone: str,
        message: str,
    ) -> NotificationResult:
        notification = SMSNotification(
            recipient_phone=recipient_phone,
            message=message,
        )
        return await self.sms_provider.send(notification)

    async def notify_breach(
        self,
        email: str,
        phone: Optional[str],
        name: str,
        breach_type: str,
        affected_data: List[str],
        actions_taken: str,
    ) -> Dict[str, NotificationResult]:
        html = f"""
        <html><body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: #dc2626;">URGENT: Data Breach Notification</h2>
        <p>Dear {name},</p>
        <p>We are writing to inform you of a data breach incident.</p>
        <p><strong>Type of Breach:</strong> {breach_type}</p>
        <p><strong>Affected Data:</strong> {", ".join(affected_data)}</p>
        <p><strong>Actions Taken:</strong> {actions_taken}</p>
        <p style="color: #6b7280; font-size: 12px; margin-top: 20px;">
        As per DPDP Act requirements, we are notifying you within 72 hours.
        </p></body></html>
        """

        results = {}
        results["email"] = await self.send_email(
            email, "URGENT: Data Breach Notification", html, name
        )

        if phone:
            sms_msg = f"SECURITY ALERT: Data breach detected. Type: {breach_type}. Check your email for details."
            results["sms"] = await self.send_sms(phone, sms_msg)

        return results

    async def send_consent_expiry_reminder(
        self,
        principal_id: UUID,
        consent_id: UUID,
        days_remaining: int,
        fiduciary_name: str,
    ) -> UUID:
        return await self.create_notification(
            principal_id=principal_id,
            notification_type=NotificationType.CONSENT_EXPIRING,
            title=f"Consent Expiring Soon",
            message=f"Your consent with {fiduciary_name} will expire in {days_remaining} days. Please review and renew if needed.",
            action_url=f"/consents/{consent_id}",
            extra_data={"consent_id": str(consent_id), "days_remaining": days_remaining},
        )

    async def send_consent_expired_notification(
        self,
        principal_id: UUID,
        consent_id: UUID,
        fiduciary_name: str,
    ) -> UUID:
        return await self.create_notification(
            principal_id=principal_id,
            notification_type=NotificationType.CONSENT_EXPIRED,
            title="Consent Expired",
            message=f"Your consent with {fiduciary_name} has expired. Data processing for this consent has stopped.",
            action_url=f"/consents/{consent_id}",
            extra_data={"consent_id": str(consent_id)},
        )

    async def send_revocation_confirmation(
        self,
        principal_id: UUID,
        consent_id: UUID,
        fiduciary_name: str,
    ) -> UUID:
        return await self.create_notification(
            principal_id=principal_id,
            notification_type=NotificationType.CONSENT_REVOKED,
            title="Consent Revoked Successfully",
            message=f"Your consent with {fiduciary_name} has been revoked. The fiduciary will stop processing your data.",
            action_url=f"/consents/{consent_id}",
            extra_data={"consent_id": str(consent_id)},
        )

    async def send_grievance_update(
        self,
        principal_id: UUID,
        grievance_id: UUID,
        status: str,
        message: str,
    ) -> UUID:
        return await self.create_notification(
            principal_id=principal_id,
            notification_type=NotificationType.GRIEVANCE_ACKNOWLEDGED
            if status == "ACKNOWLEDGED"
            else NotificationType.GRIEVANCE_RESOLVED,
            title=f"Grievance {status.title()}",
            message=message,
            action_url=f"/grievances/{grievance_id}",
            extra_data={"grievance_id": str(grievance_id), "status": status},
        )

    async def send_deletion_notification(
        self,
        principal_id: UUID,
        deletion_request_id: UUID,
        status: str,
        message: str,
    ) -> UUID:
        return await self.create_notification(
            principal_id=principal_id,
            notification_type=NotificationType.DELETION_REQUESTED
            if status == "PENDING"
            else NotificationType.DELETION_COMPLETED,
            title=f"Data Deletion {status.title()}",
            message=message,
            action_url=f"/deletion/{deletion_request_id}",
            extra_data={"deletion_request_id": str(deletion_request_id), "status": status},
        )

    async def get_unread_notifications(
        self,
        principal_id: UUID,
        limit: int = 20,
    ) -> List[Any]:
        from api.database import NotificationDB

        result = await self.db.execute(
            select(NotificationDB)
            .where(
                and_(
                    NotificationDB.principal_id == principal_id,
                    NotificationDB.read == False,
                )
            )
            .order_by(NotificationDB.created_at.desc())
            .limit(limit)
        )
        return result.scalars().all()

    async def mark_as_read(self, notification_id: UUID) -> bool:
        from api.database import NotificationDB

        result = await self.db.execute(
            update(NotificationDB)
            .where(NotificationDB.id == notification_id)
            .values(read=True, read_at=datetime.now(timezone.utc))
        )
        await self.db.commit()
        return result.rowcount > 0

    async def mark_all_as_read(self, principal_id: UUID) -> int:
        from api.database import NotificationDB

        result = await self.db.execute(
            update(NotificationDB)
            .where(
                and_(
                    NotificationDB.principal_id == principal_id,
                    NotificationDB.read == False,
                )
            )
            .values(read=True, read_at=datetime.now(timezone.utc))
        )
        await self.db.commit()
        return result.rowcount
