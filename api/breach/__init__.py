"""Breach Notification System - DPDP Act Section 8 Compliance.

Implements breach detection, notification to authorities, and affected principal communication.
"""

import os
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4
from enum import Enum
from dataclasses import dataclass

from pydantic import BaseModel, Field
from sqlalchemy import select, and_, update
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class BreachSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class BreachStatus(str, Enum):
    DETECTED = "DETECTED"
    INVESTIGATING = "INVESTIGATING"
    CONTAINED = "CONTAINED"
    NOTIFIED_AUTHORITY = "NOTIFIED_AUTHORITY"
    NOTIFIED_PRINCIPALS = "NOTIFIED_PRINCIPALS"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


class BreachType(str, Enum):
    UNAUTHORIZED_ACCESS = "UNAUTHORIZED_ACCESS"
    DATA_EXFILTRATION = "DATA_EXFILTRATION"
    MALWARE = "MALWARE"
    PHISHING = "PHISHING"
    INSIDER_THREAT = "INSIDER_THREAT"
    SYSTEM_VULNERABILITY = "SYSTEM_VULNERABILITY"
    THIRD_PARTY_BREACH = "THIRD_PARTY_BREACH"
    PHYSICAL_THEFT = "PHYSICAL_THEFT"
    ACCIDENTAL_DISCLOSURE = "ACCIDENTAL_DISCLOSURE"
    OTHER = "OTHER"


@dataclass
class BreachRecord:
    id: UUID
    fiduciary_id: UUID
    breach_type: BreachType
    severity: BreachSeverity
    status: BreachStatus
    detected_at: datetime
    description: str
    affected_principals_count: int
    data_categories_involved: List[str]
    containment_measures: Optional[List[str]] = None
    authority_notified_at: Optional[datetime] = None
    principals_notified_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    created_at: datetime = None


class BreachCreate(BaseModel):
    fiduciary_id: UUID
    breach_type: BreachType
    severity: BreachSeverity
    description: str = Field(..., min_length=50)
    detected_at: datetime
    affected_principals_count: int = Field(..., ge=0)
    data_categories_involved: List[str] = Field(..., min_length=1)
    containment_measures: Optional[List[str]] = None
    third_parties_involved: Optional[List[str]] = None


class BreachUpdate(BaseModel):
    status: Optional[BreachStatus] = None
    containment_measures: Optional[List[str]] = None
    additional_description: Optional[str] = None
    affected_principals_count: Optional[int] = None


class AuthorityNotification(BaseModel):
    breach_id: UUID
    authority_name: str = "Data Protection Board of India"
    notification_method: str = "email"
    notification_timestamp: datetime
    reference_number: Optional[str] = None


class PrincipalNotification(BaseModel):
    breach_id: UUID
    principal_id: UUID
    notification_method: str
    notification_timestamp: datetime
    delivery_status: str


class BreachNotificationService:
    """
    Service for managing data breach notifications.

    Per DPDP Act Section 8:
    - Notify Data Protection Board within 72 hours of breach detection
    - Notify affected principals without undue delay
    - Document all breach details and remediation measures
    """

    AUTHORITY_NOTIFICATION_DEADLINE_HOURS = 72
    PRINCIPAL_NOTIFICATION_DEADLINE_HOURS = 168  # 7 days

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_breach(
        self,
        data: BreachCreate,
    ) -> BreachRecord:
        """Create a new breach record."""
        from api.database import BreachRecordDB

        breach_id = uuid4()

        db_record = BreachRecordDB(
            id=breach_id,
            fiduciary_id=data.fiduciary_id,
            breach_type=data.breach_type.value,
            severity=data.severity.value,
            status=BreachStatus.DETECTED.value,
            detected_at=data.detected_at,
            description=data.description,
            affected_principals_count=data.affected_principals_count,
            data_categories_involved=json.dumps(data.data_categories_involved),
            containment_measures=json.dumps(data.containment_measures)
            if data.containment_measures
            else None,
            third_parties_involved=json.dumps(data.third_parties_involved)
            if data.third_parties_involved
            else None,
        )

        self.db.add(db_record)
        await self.db.commit()

        logger.critical(
            f"Breach detected: {breach_id} - Type: {data.breach_type.value}, "
            f"Severity: {data.severity.value}, Affected: {data.affected_principals_count}"
        )

        return BreachRecord(
            id=breach_id,
            fiduciary_id=data.fiduciary_id,
            breach_type=data.breach_type,
            severity=data.severity,
            status=BreachStatus.DETECTED,
            detected_at=data.detected_at,
            description=data.description,
            affected_principals_count=data.affected_principals_count,
            data_categories_involved=data.data_categories_involved,
            containment_measures=data.containment_measures,
            created_at=datetime.now(timezone.utc),
        )

    async def get_breach(self, breach_id: UUID) -> Optional[BreachRecord]:
        """Get breach record by ID."""
        from api.database import BreachRecordDB

        result = await self.db.execute(select(BreachRecordDB).where(BreachRecordDB.id == breach_id))
        db_record = result.scalar_one_or_none()

        if not db_record:
            return None

        return self._db_to_record(db_record)

    async def list_breaches(
        self,
        fiduciary_id: Optional[UUID] = None,
        status: Optional[BreachStatus] = None,
        severity: Optional[BreachSeverity] = None,
        from_date: Optional[datetime] = None,
        limit: int = 50,
    ) -> List[BreachRecord]:
        """List breaches with optional filters."""
        from api.database import BreachRecordDB

        query = select(BreachRecordDB)

        if fiduciary_id:
            query = query.where(BreachRecordDB.fiduciary_id == fiduciary_id)
        if status:
            query = query.where(BreachRecordDB.status == status.value)
        if severity:
            query = query.where(BreachRecordDB.severity == severity.value)
        if from_date:
            query = query.where(BreachRecordDB.detected_at >= from_date)

        query = query.order_by(BreachRecordDB.detected_at.desc()).limit(limit)

        result = await self.db.execute(query)
        records = result.scalars().all()

        return [self._db_to_record(r) for r in records]

    async def notify_authority(
        self,
        breach_id: UUID,
        notified_by: str,
    ) -> AuthorityNotification:
        """
        Notify Data Protection Board of India about the breach.

        Must be done within 72 hours of breach detection per DPDP Act.
        """
        from api.database import BreachRecordDB

        breach = await self.get_breach(breach_id)
        if not breach:
            raise ValueError("Breach not found")

        notification = AuthorityNotification(
            breach_id=breach_id,
            authority_name="Data Protection Board of India",
            notification_method="email",
            notification_timestamp=datetime.now(timezone.utc),
            reference_number=f"DPBI-{breach_id.hex[:8].upper()}",
        )

        await self.db.execute(
            update(BreachRecordDB)
            .where(BreachRecordDB.id == breach_id)
            .values(
                status=BreachStatus.NOTIFIED_AUTHORITY.value,
                authority_notified_at=notification.notification_timestamp,
                authority_reference_number=notification.reference_number,
            )
        )
        await self.db.commit()

        logger.critical(
            f"Authority notified for breach {breach_id}: Reference: {notification.reference_number}"
        )

        return notification

    async def notify_principals(
        self,
        breach_id: UUID,
        principal_ids: List[UUID],
        notification_method: str = "email",
    ) -> List[PrincipalNotification]:
        """
        Notify affected principals about the breach.

        Per DPDP Act, must be done without undue delay after containment.
        """
        from api.database import BreachRecordDB, DataPrincipalDB
        from api.notifications import NotificationService, NotificationType

        breach = await self.get_breach(breach_id)
        if not breach:
            raise ValueError("Breach not found")

        notifications = []
        notification_service = NotificationService(self.db)

        for principal_id in principal_ids:
            notification = PrincipalNotification(
                breach_id=breach_id,
                principal_id=principal_id,
                notification_method=notification_method,
                notification_timestamp=datetime.now(timezone.utc),
                delivery_status="PENDING",
            )
            notifications.append(notification)

            result = await self.db.execute(
                select(DataPrincipalDB).where(DataPrincipalDB.id == principal_id)
            )
            principal = result.scalar_one_or_none()

            if principal:
                try:
                    html_body = self._generate_principal_html_email(breach, principal)

                    if principal.email:
                        email_result = await notification_service.send_email(
                            recipient_email=principal.email,
                            subject="URGENT: Data Security Incident Notification",
                            html_body=html_body,
                            recipient_name=principal.name,
                        )
                        notification.delivery_status = (
                            "DELIVERED" if email_result.success else "FAILED"
                        )
                        logger.info(
                            f"Breach email sent to principal {principal_id}: {email_result.success}"
                        )

                    if principal.phone and notification_method == "sms":
                        sms_message = (
                            f"SECURITY ALERT: We have detected a data security incident "
                            f"that may affect your personal information. Type: {breach.breach_type.value}. "
                            f"Check your email for details or contact support."
                        )
                        sms_result = await notification_service.send_sms(
                            recipient_phone=principal.phone,
                            message=sms_message,
                        )
                        logger.info(
                            f"Breach SMS sent to principal {principal_id}: {sms_result.success}"
                        )

                    in_app_result = await notification_service.create_notification(
                        principal_id=principal_id,
                        notification_type=NotificationType.BREACH_NOTIFICATION,
                        title="Data Security Incident",
                        message=f"A data breach has been detected. Please check your email for details.",
                        action_url=f"/breach/{breach_id}",
                        extra_data={
                            "breach_id": str(breach_id),
                            "breach_type": breach.breach_type.value,
                            "severity": breach.severity.value,
                        },
                    )
                    logger.info(f"In-app notification created: {in_app_result}")

                except Exception as e:
                    notification.delivery_status = f"ERROR: {str(e)[:50]}"
                    logger.error(f"Failed to notify principal {principal_id}: {e}")

        await self.db.execute(
            update(BreachRecordDB)
            .where(BreachRecordDB.id == breach_id)
            .values(
                status=BreachStatus.NOTIFIED_PRINCIPALS.value,
                principals_notified_at=datetime.now(timezone.utc),
            )
        )
        await self.db.commit()

        logger.info(f"Principals notified for breach {breach_id}: {len(notifications)} principals")

        return notifications

    def _generate_principal_html_email(self, breach: BreachRecord, principal) -> str:
        """Generate HTML email for principal notification."""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #dc2626; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; background-color: #f9fafb; }}
                .section {{ margin-bottom: 20px; }}
                .section-title {{ font-weight: bold; color: #374151; margin-bottom: 10px; }}
                ul {{ margin: 0; padding-left: 20px; }}
                .footer {{ text-align: center; color: #6b7280; font-size: 12px; margin-top: 20px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>⚠️ Data Security Incident Notification</h1>
            </div>
            <div class="content">
                <p>Dear {principal.name if principal.name else "Valued User"},</p>
                
                <p>We are writing to inform you of a data security incident that may have affected your personal information. This notification is being sent in accordance with the Digital Personal Data Protection Act, 2023.</p>
                
                <div class="section">
                    <div class="section-title">What Happened:</div>
                    <p>{breach.description}</p>
                </div>
                
                <div class="section">
                    <div class="section-title">Type of Incident:</div>
                    <p>{breach.breach_type.value.replace("_", " ").title()}</p>
                </div>
                
                <div class="section">
                    <div class="section-title">What Information Was Involved:</div>
                    <ul>
                        {chr(10).join(f"<li>{cat}</li>" for cat in breach.data_categories_involved)}
                    </ul>
                </div>
                
                <div class="section">
                    <div class="section-title">What We Are Doing:</div>
                    <ul>
                        {chr(10).join(f"<li>{m}</li>" for m in (breach.containment_measures or ["Investigating and implementing additional security measures"]))}
                    </ul>
                </div>
                
                <div class="section">
                    <div class="section-title">What You Can Do:</div>
                    <ul>
                        <li>Monitor your accounts for any suspicious activity</li>
                        <li>Be cautious of phishing emails or messages</li>
                        <li>Report any unauthorized access immediately</li>
                        <li>Contact us if you have any questions</li>
                    </ul>
                </div>
                
                <p>We take your privacy and security seriously and sincerely apologize for any concern this incident may cause.</p>
                
                <p>If you have any questions or need assistance, please contact our Data Protection Officer.</p>
            </div>
            <div class="footer">
                <p>This notification is sent in compliance with the Digital Personal Data Protection Act, 2023.</p>
                <p>Breach Reference: {breach.id}</p>
            </div>
        </body>
        </html>
        """

    async def send_authority_notification_email(
        self,
        breach_id: UUID,
        authority_email: str = "breach-notifications@dpb.gov.in",
    ) -> Dict[str, Any]:
        """Send actual email notification to Data Protection Board."""
        from api.notifications import NotificationService

        breach = await self.get_breach(breach_id)
        if not breach:
            raise ValueError("Breach not found")

        notification_service = NotificationService(self.db)

        reference_number = f"DPBI-{breach_id.hex[:8].upper()}"
        email_body = BreachNotificationTemplate.authority_notification_email(
            breach, reference_number
        )

        result = await notification_service.send_email(
            recipient_email=authority_email,
            subject=f"Data Breach Notification - Reference: {reference_number}",
            html_body=f"<pre>{email_body}</pre>",
        )

        return {
            "success": result.success,
            "reference_number": reference_number,
            "notification_id": result.notification_id,
            "error": result.error,
        }

    async def update_breach_status(
        self,
        breach_id: UUID,
        status: BreachStatus,
        additional_info: Optional[str] = None,
    ) -> BreachRecord:
        """Update breach status."""
        from api.database import BreachRecordDB

        update_data = {"status": status.value}

        if status == BreachStatus.RESOLVED:
            update_data["resolved_at"] = datetime.now(timezone.utc)

        if additional_info:
            result = await self.db.execute(
                select(BreachRecordDB.description).where(BreachRecordDB.id == breach_id)
            )
            current_desc = result.scalar_one()
            update_data["description"] = f"{current_desc}\n\nUpdate: {additional_info}"

        await self.db.execute(
            update(BreachRecordDB).where(BreachRecordDB.id == breach_id).values(**update_data)
        )
        await self.db.commit()

        logger.info(f"Breach {breach_id} status updated to {status.value}")

        return await self.get_breach(breach_id)

    async def check_notification_deadlines(self) -> List[Dict[str, Any]]:
        """
        Check for breaches approaching or past notification deadlines.

        Returns list of breaches requiring attention.
        """
        from api.database import BreachRecordDB

        now = datetime.now(timezone.utc)
        authority_deadline = now - timedelta(hours=self.AUTHORITY_NOTIFICATION_DEADLINE_HOURS)
        principal_deadline = now - timedelta(hours=self.PRINCIPAL_NOTIFICATION_DEADLINE_HOURS)

        result = await self.db.execute(
            select(BreachRecordDB).where(
                and_(
                    BreachRecordDB.status.in_(
                        [
                            BreachStatus.DETECTED.value,
                            BreachStatus.INVESTIGATING.value,
                            BreachStatus.CONTAINED.value,
                            BreachStatus.NOTIFIED_AUTHORITY.value,
                        ]
                    ),
                )
            )
        )
        breaches = result.scalars().all()

        alerts = []
        for breach in breaches:
            breach_data = {
                "breach_id": str(breach.id),
                "fiduciary_id": str(breach.fiduciary_id),
                "severity": breach.severity,
                "detected_at": breach.detected_at.isoformat(),
            }

            hours_since_detection = (now - breach.detected_at).total_seconds() / 3600

            if breach.status in [
                BreachStatus.DETECTED.value,
                BreachStatus.INVESTIGATING.value,
                BreachStatus.CONTAINED.value,
            ]:
                if hours_since_detection > self.AUTHORITY_NOTIFICATION_DEADLINE_HOURS:
                    breach_data["alert"] = "OVERDUE_AUTHORITY_NOTIFICATION"
                    breach_data["hours_overdue"] = (
                        hours_since_detection - self.AUTHORITY_NOTIFICATION_DEADLINE_HOURS
                    )
                    alerts.append(breach_data)
                elif hours_since_detection > self.AUTHORITY_NOTIFICATION_DEADLINE_HOURS - 12:
                    breach_data["alert"] = "APPROACHING_AUTHORITY_DEADLINE"
                    breach_data["hours_remaining"] = (
                        self.AUTHORITY_NOTIFICATION_DEADLINE_HOURS - hours_since_detection
                    )
                    alerts.append(breach_data)

            if breach.status == BreachStatus.NOTIFIED_AUTHORITY.value:
                if hours_since_detection > self.PRINCIPAL_NOTIFICATION_DEADLINE_HOURS:
                    breach_data["alert"] = "OVERDUE_PRINCIPAL_NOTIFICATION"
                    breach_data["hours_overdue"] = (
                        hours_since_detection - self.PRINCIPAL_NOTIFICATION_DEADLINE_HOURS
                    )
                    alerts.append(breach_data)

        return alerts

    def _db_to_record(self, db_record) -> BreachRecord:
        """Convert database record to dataclass."""
        return BreachRecord(
            id=db_record.id,
            fiduciary_id=db_record.fiduciary_id,
            breach_type=BreachType(db_record.breach_type),
            severity=BreachSeverity(db_record.severity),
            status=BreachStatus(db_record.status),
            detected_at=db_record.detected_at,
            description=db_record.description,
            affected_principals_count=db_record.affected_principals_count,
            data_categories_involved=json.loads(db_record.data_categories_involved),
            containment_measures=json.loads(db_record.containment_measures)
            if db_record.containment_measures
            else None,
            authority_notified_at=db_record.authority_notified_at,
            principals_notified_at=db_record.principals_notified_at,
            resolved_at=db_record.resolved_at,
            created_at=db_record.created_at,
        )


class BreachNotificationTemplate:
    """Templates for breach notifications."""

    @staticmethod
    def authority_notification_email(breach: BreachRecord, reference_number: str) -> str:
        return f"""
Subject: Data Breach Notification - Reference: {reference_number}

To: Data Protection Board of India

This is to notify you of a personal data breach as required under Section 8 of the 
Digital Personal Data Protection Act, 2023.

BREACH DETAILS:
- Reference Number: {reference_number}
- Date Detected: {breach.detected_at.isoformat()}
- Breach Type: {breach.breach_type.value}
- Severity: {breach.severity.value}
- Affected Principals: {breach.affected_principals_count}

DATA CATEGORIES AFFECTED:
{chr(10).join(f"- {cat}" for cat in breach.data_categories_involved)}

DESCRIPTION:
{breach.description}

CONTAINMENT MEASURES:
{chr(10).join(f"- {m}" for m in (breach.containment_measures or ["In progress"]))}

This notification is made within the required 72-hour timeframe.

Please contact us for any additional information required.

Sincerely,
Data Protection Officer
"""

    @staticmethod
    def principal_notification_email(breach: BreachRecord) -> str:
        return f"""
Subject: Important Notice: Data Security Incident

Dear Valued User,

We are writing to inform you of a data security incident that may have affected 
your personal information.

WHAT HAPPENED:
{breach.description}

WHAT INFORMATION WAS INVOLVED:
{chr(10).join(f"- {cat}" for cat in breach.data_categories_involved)}

WHAT WE ARE DOING:
{chr(10).join(f"- {m}" for m in (breach.containment_measures or ["Investigating and implementing additional security measures"]))}

WHAT YOU CAN DO:
- Monitor your accounts for suspicious activity
- Report any unauthorized access immediately
- Contact us if you have questions

For questions or assistance, please contact our Data Protection Officer.

We take your privacy seriously and apologize for any concern this may cause.

Sincerely,
Data Protection Team
"""
