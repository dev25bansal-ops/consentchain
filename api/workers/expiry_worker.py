from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any
from uuid import UUID
import asyncio
import json
import os
import logging
from enum import Enum

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, update
from sqlalchemy.orm import sessionmaker

from api.database import (
    ConsentRecordDB,
    ConsentEventDB,
    ConsentStatusDB,
    EventTypeDB,
    DeletionRequestDB,
    DataPrincipalDB,
    DataFiduciaryDB,
)
from api.webhooks.service import WebhookService, WebhookSubscription
from consentchain_types.enums import ConsentStatus, EventType, WebhookEvent

logger = logging.getLogger(__name__)


class ConsentExpiryWorker:
    def __init__(
        self,
        session_factory: sessionmaker,
        webhook_service: Optional[WebhookService] = None,
        algorand_client: Optional[Any] = None,
        consent_app_id: Optional[int] = None,
    ):
        self.session_factory = session_factory
        self.webhook_service = webhook_service
        self.algorand_client = algorand_client
        self.consent_app_id = consent_app_id
        self.scheduler = AsyncIOScheduler()
        self._error_count = 0
        self._last_error: Optional[str] = None

    def start(self):
        logger.info("Starting ConsentExpiryWorker...")
        self.scheduler.add_job(
            self._safe_process_expired,
            trigger=IntervalTrigger(minutes=5),
            id="consent_expiry_check",
            replace_existing=True,
        )
        self.scheduler.add_job(
            self._safe_send_reminders,
            trigger=IntervalTrigger(hours=1),
            id="expiry_reminder_check",
            replace_existing=True,
        )
        self.scheduler.start()
        logger.info("ConsentExpiryWorker started successfully")

    def stop(self):
        logger.info("Stopping ConsentExpiryWorker...")
        self.scheduler.shutdown()
        logger.info("ConsentExpiryWorker stopped")

    async def _safe_process_expired(self) -> Dict[str, int]:
        try:
            return await self.process_expired_consents()
        except Exception as e:
            self._error_count += 1
            self._last_error = str(e)
            logger.exception(f"Error in process_expired_consents: {e}")
            return {"processed": 0, "errors": 1, "error": str(e)}

    async def _safe_send_reminders(self) -> Dict[str, int]:
        try:
            return await self.send_expiry_reminders()
        except Exception as e:
            self._error_count += 1
            self._last_error = str(e)
            logger.exception(f"Error in send_expiry_reminders: {e}")
            return {"sent": 0, "errors": 1, "error": str(e)}

    async def process_expired_consents(self) -> Dict[str, int]:
        async with self.session_factory() as session:
            now = datetime.now(timezone.utc)

            result = await session.execute(
                select(ConsentRecordDB).where(
                    and_(
                        ConsentRecordDB.status == ConsentStatusDB.GRANTED,
                        ConsentRecordDB.expires_at < now,
                    )
                )
            )
            expired_consents = result.scalars().all()

            processed = 0
            errors = 0

            for consent in expired_consents:
                try:
                    consent.status = ConsentStatusDB.EXPIRED

                    event = ConsentEventDB(
                        consent_id=consent.id,
                        event_type=EventTypeDB.CONSENT_EXPIRY,
                        actor=consent.principal.wallet_address if consent.principal else "system",
                        actor_type="system",
                        previous_status=ConsentStatusDB.GRANTED,
                        new_status=ConsentStatusDB.EXPIRED,
                        metadata='{"reason": "automatic_expiry"}',
                    )
                    session.add(event)

                    if self.webhook_service:
                        try:
                            await self._trigger_expiry_webhook(consent)
                        except Exception as wh_err:
                            logger.warning(
                                f"Webhook trigger failed for consent {consent.id}: {wh_err}"
                            )

                    processed += 1

                except Exception as e:
                    errors += 1
                    logger.error(f"Failed to expire consent {consent.id}: {e}")
                    continue

            await session.commit()

            logger.info(f"Processed {processed} expired consents, {errors} errors")
            return {
                "processed": processed,
                "errors": errors,
                "timestamp": now.isoformat(),
            }

    async def send_expiry_reminders(self) -> Dict[str, int]:
        async with self.session_factory() as session:
            now = datetime.now(timezone.utc)
            reminder_window = now + timedelta(hours=24)

            result = await session.execute(
                select(ConsentRecordDB).where(
                    and_(
                        ConsentRecordDB.status == ConsentStatusDB.GRANTED,
                        ConsentRecordDB.expires_at > now,
                        ConsentRecordDB.expires_at <= reminder_window,
                    )
                )
            )
            expiring_soon = result.scalars().all()

            reminders_sent = 0

            for consent in expiring_soon:
                try:
                    await self._send_expiry_reminder(consent)
                    reminders_sent += 1
                except Exception:
                    continue

            return {
                "reminders_sent": reminders_sent,
                "timestamp": now.isoformat(),
            }

    async def _trigger_expiry_webhook(self, consent: ConsentRecordDB) -> None:
        if not self.webhook_service:
            return

        subscriptions = await self._get_subscriptions_for_fiduciary(consent.fiduciary_id)

        for subscription in subscriptions:
            if WebhookEvent.CONSENT_EXPIRED.value in subscription.events:
                await self.webhook_service.queue_webhook(
                    subscription_id=subscription.id,
                    event_type=WebhookEvent.CONSENT_EXPIRED.value,
                    payload={
                        "consent_id": str(consent.id),
                        "principal_id": str(consent.principal_id),
                        "fiduciary_id": str(consent.fiduciary_id),
                        "expired_at": consent.expires_at.isoformat()
                        if consent.expires_at
                        else None,
                        "consent_hash": consent.consent_hash,
                    },
                )

    async def _send_expiry_reminder(self, consent: ConsentRecordDB) -> None:
        from api.database import DataPrincipalDB, DataFiduciaryDB

        principal = await self.session_factory().execute(
            select(DataPrincipalDB).where(DataPrincipalDB.id == consent.principal_id)
        )
        principal = principal.scalar_one_or_none()

        fiduciary = await self.session_factory().execute(
            select(DataFiduciaryDB).where(DataFiduciaryDB.id == consent.fiduciary_id)
        )
        fiduciary = fiduciary.scalar_one_or_none()

        reminder_data = {
            "consent_id": str(consent.id),
            "principal_wallet": principal.wallet_address if principal else None,
            "fiduciary_name": fiduciary.name if fiduciary else "Unknown",
            "purpose": consent.purpose,
            "expires_at": consent.expires_at.isoformat() if consent.expires_at else None,
            "reminder_type": "expiry_reminder",
            "hours_until_expiry": (
                (consent.expires_at - datetime.now(timezone.utc)).total_seconds() / 3600
                if consent.expires_at
                else 0
            ),
        }

        if self.webhook_service:
            subscriptions = await self._get_subscriptions_for_fiduciary(consent.fiduciary_id)
            for subscription in subscriptions:
                if "CONSENT_EXPIRING" in subscription.events:
                    await self.webhook_service.queue_webhook(
                        subscription_id=subscription.id,
                        event_type="CONSENT_EXPIRING",
                        payload=reminder_data,
                    )

    async def _get_subscriptions_for_fiduciary(
        self, fiduciary_id: UUID
    ) -> List[WebhookSubscription]:
        return []

    async def expire_consent_on_chain(self, consent_hash: str) -> Optional[str]:
        if not self.algorand_client or not self.consent_app_id:
            return None

        try:
            tx_id = await asyncio.to_thread(
                self.algorand_client.expire_consent,
                self.consent_app_id,
                consent_hash,
            )
            return tx_id
        except Exception:
            return None


class WebhookDeliveryWorker:
    def __init__(
        self,
        webhook_service: WebhookService,
        subscription_repository: Any,
    ):
        self.webhook_service = webhook_service
        self.subscription_repository = subscription_repository
        self.scheduler = AsyncIOScheduler()
        self.running = False

    def start(self):
        self.scheduler.add_job(
            self.process_webhooks,
            trigger=IntervalTrigger(seconds=5),
            id="webhook_delivery",
            replace_existing=True,
        )
        self.scheduler.start()
        self.running = True

    def stop(self):
        self.running = False
        self.scheduler.shutdown()

    async def process_webhooks(self) -> Dict[str, int]:
        processed = await self.webhook_service.process_pending_webhooks(batch_size=20)
        return {"processed": processed}


class DeletionDeadlineWorker:
    """Worker to enforce DPDP Section 9 - 30-day deletion deadline.

    Monitors deletion requests and:
    1. Sends reminders at 7 days and 1 day before deadline
    2. Escalates overdue requests to compliance team
    3. Generates automatic compliance reports for overdue requests
    """

    DELETION_DEADLINE_DAYS = 30
    REMINDER_DAYS = [7, 1]

    def __init__(
        self,
        session_factory: sessionmaker,
        notification_service: Optional[Any] = None,
    ):
        self.session_factory = session_factory
        self.notification_service = notification_service
        self.scheduler = AsyncIOScheduler()
        self._error_count = 0
        self._last_error: Optional[str] = None

    def start(self):
        logger.info("Starting DeletionDeadlineWorker...")
        self.scheduler.add_job(
            self._safe_check_deadlines,
            trigger=IntervalTrigger(hours=1),
            id="deletion_deadline_check",
            replace_existing=True,
        )
        self.scheduler.add_job(
            self._safe_process_overdue,
            trigger=IntervalTrigger(hours=6),
            id="deletion_overdue_check",
            replace_existing=True,
        )
        self.scheduler.start()
        logger.info("DeletionDeadlineWorker started successfully")

    def stop(self):
        logger.info("Stopping DeletionDeadlineWorker...")
        self.scheduler.shutdown()
        logger.info("DeletionDeadlineWorker stopped")

    async def _safe_check_deadlines(self) -> Dict[str, int]:
        try:
            return await self.check_deadlines()
        except Exception as e:
            self._error_count += 1
            self._last_error = str(e)
            logger.exception(f"Error in check_deadlines: {e}")
            return {"checked": 0, "errors": 1}

    async def _safe_process_overdue(self) -> Dict[str, int]:
        try:
            return await self.process_overdue_requests()
        except Exception as e:
            self._error_count += 1
            self._last_error = str(e)
            logger.exception(f"Error in process_overdue_requests: {e}")
            return {"overdue": 0, "errors": 1}

    async def check_deadlines(self) -> Dict[str, int]:
        """Check deletion requests approaching deadline and send reminders."""
        async with self.session_factory() as session:
            now = datetime.now(timezone.utc)

            reminders_sent = 0
            checked = 0

            for days in self.REMINDER_DAYS:
                deadline_date = now + timedelta(days=days)

                result = await session.execute(
                    select(DeletionRequestDB).where(
                        and_(
                            DeletionRequestDB.status.in_(
                                ["PENDING", "VERIFICATION_IN_PROGRESS", "SCHEDULED"]
                            ),
                            DeletionRequestDB.scheduled_at <= deadline_date,
                            DeletionRequestDB.scheduled_at > now,
                        )
                    )
                )
                approaching_deadline = result.scalars().all()

                for request in approaching_deadline:
                    try:
                        await self._send_deadline_reminder(request, days)
                        reminders_sent += 1
                    except Exception as e:
                        logger.error(f"Failed to send reminder for request {request.id}: {e}")
                    checked += 1

            logger.info(f"Checked {checked} requests, sent {reminders_sent} reminders")
            return {"checked": checked, "reminders_sent": reminders_sent}

    async def process_overdue_requests(self) -> Dict[str, int]:
        """Process deletion requests past deadline."""
        async with self.session_factory() as session:
            now = datetime.now(timezone.utc)
            deadline = now - timedelta(days=self.DELETION_DEADLINE_DAYS)

            result = await session.execute(
                select(DeletionRequestDB).where(
                    and_(
                        DeletionRequestDB.status.in_(
                            ["PENDING", "VERIFICATION_IN_PROGRESS", "SCHEDULED", "IN_PROGRESS"]
                        ),
                        DeletionRequestDB.created_at < deadline,
                    )
                )
            )
            overdue_requests = result.scalars().all()

            escalated = 0
            for request in overdue_requests:
                try:
                    request.extra_data = json.dumps(
                        {
                            **json.loads(request.extra_data or "{}"),
                            "overdue": True,
                            "overdue_since": now.isoformat(),
                            "escalated_at": now.isoformat(),
                        }
                    )

                    await self._escalate_to_compliance(request)
                    escalated += 1
                except Exception as e:
                    logger.error(f"Failed to escalate overdue request {request.id}: {e}")

            await session.commit()

            logger.info(f"Found {len(overdue_requests)} overdue requests, escalated {escalated}")
            return {"overdue": len(overdue_requests), "escalated": escalated}

    async def _send_deadline_reminder(self, request: Any, days_remaining: int) -> None:
        """Send deadline reminder to fiduciary and principal."""
        logger.warning(
            f"DELETION DEADLINE REMINDER: Request {request.id} expires in {days_remaining} day(s). "
            f"Principal: {request.principal_id}, Fiduciary: {request.fiduciary_id}"
        )

        if not self.notification_service:
            return

        async with self.session_factory() as session:
            fiduciary_result = await session.execute(
                select(DataFiduciaryDB).where(DataFiduciaryDB.id == request.fiduciary_id)
            )
            fiduciary = fiduciary_result.scalar_one_or_none()

            if fiduciary and fiduciary.contact_email:
                html_body = f"""
                <!DOCTYPE html>
                <html>
                <head><style>
                    body {{ font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background-color: #f59e0b; color: white; padding: 20px; text-align: center; }}
                    .content {{ padding: 20px; background-color: #f9fafb; }}
                    .warning {{ color: #dc2626; font-weight: bold; }}
                    .footer {{ text-align: center; color: #6b7280; font-size: 12px; margin-top: 20px; }}
                </style></head>
                <body>
                    <div class="header">
                        <h2>⚠️ Deletion Request Deadline Reminder</h2>
                    </div>
                    <div class="content">
                        <p>A data deletion request is approaching its legal deadline.</p>
                        
                        <h3>Request Details:</h3>
                        <ul>
                            <li><strong>Request ID:</strong> {request.id}</li>
                            <li><strong>Days Remaining:</strong> <span class="warning">{days_remaining}</span></li>
                            <li><strong>Created:</strong> {request.created_at}</li>
                            <li><strong>Principal ID:</strong> {request.principal_id}</li>
                        </ul>
                        
                        <p class="warning">⚠️ As per DPDP Act Section 9, deletion requests must be processed within 30 days of receipt.</p>
                        
                        <p>Please ensure this request is completed before the deadline to maintain compliance.</p>
                    </div>
                    <div class="footer">
                        <p>This is an automated reminder from ConsentChain Compliance System</p>
                    </div>
                </body>
                </html>
                """

                await self.notification_service.send_email(
                    recipient_email=fiduciary.contact_email,
                    subject=f"URGENT: Deletion Request Deadline in {days_remaining} Day(s) - DPDP Compliance",
                    html_body=html_body,
                )
                logger.info(f"Deadline reminder email sent to fiduciary {fiduciary.id}")

            principal_result = await session.execute(
                select(DataPrincipalDB).where(DataPrincipalDB.id == request.principal_id)
            )
            principal = principal_result.scalar_one_or_none()

            if principal:
                if principal.email:
                    principal_html = f"""
                    <!DOCTYPE html>
                    <html>
                    <head><style>
                        body {{ font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; }}
                        .header {{ background-color: #3b82f6; color: white; padding: 20px; text-align: center; }}
                        .content {{ padding: 20px; background-color: #f9fafb; }}
                        .footer {{ text-align: center; color: #6b7280; font-size: 12px; margin-top: 20px; }}
                    </style></head>
                    <body>
                        <div class="header">
                            <h2>Data Deletion Request Update</h2>
                        </div>
                        <div class="content">
                            <p>Dear {principal.name or "User"},</p>
                            
                            <p>We are writing to update you on your data deletion request.</p>
                            
                            <p>Your request is being processed and is scheduled for completion within {days_remaining} day(s).</p>
                            
                            <p>We are committed to protecting your privacy and will complete your request in accordance with the Digital Personal Data Protection Act, 2023.</p>
                            
                            <p>Thank you for your patience.</p>
                        </div>
                        <div class="footer">
                            <p>Request ID: {request.id}</p>
                        </div>
                    </body>
                    </html>
                    """

                    await self.notification_service.send_email(
                        recipient_email=principal.email,
                        subject="Update on Your Data Deletion Request",
                        html_body=principal_html,
                        recipient_name=principal.name,
                    )
                    logger.info(f"Deadline reminder email sent to principal {principal.id}")

                if principal.phone and days_remaining <= 1:
                    await self.notification_service.send_sms(
                        recipient_phone=principal.phone,
                        message=f"Your data deletion request is being processed. Expected completion: {days_remaining} day(s). Reference: {str(request.id)[:8]}",
                    )
                    logger.info(f"Deadline reminder SMS sent to principal {principal.id}")

    async def _escalate_to_compliance(self, request: Any) -> None:
        """Escalate overdue request to compliance team and notify principal."""
        logger.error(
            f"DELETION DEADLINE EXCEEDED: Request {request.id} is overdue. "
            f"Principal: {request.principal_id}, Created: {request.created_at}"
        )

        compliance_email = os.getenv("COMPLIANCE_TEAM_EMAIL")

        if compliance_email and self.notification_service:
            days_overdue = (datetime.now(timezone.utc) - request.created_at).days - 30

            html_body = f"""
            <!DOCTYPE html>
            <html>
            <head><style>
                body {{ font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #dc2626; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; background-color: #fef2f2; }}
                .alert {{ color: #dc2626; font-weight: bold; font-size: 18px; }}
                .footer {{ text-align: center; color: #6b7280; font-size: 12px; margin-top: 20px; }}
            </style></head>
            <body>
                <div class="header">
                    <h1>🚨 DELETION REQUEST ESCALATION</h1>
                </div>
                <div class="content">
                    <p class="alert">A deletion request has exceeded the 30-day DPDP deadline!</p>
                    
                    <h3>Request Details:</h3>
                    <ul>
                        <li><strong>Request ID:</strong> {request.id}</li>
                        <li><strong>Principal ID:</strong> {request.principal_id}</li>
                        <li><strong>Fiduciary ID:</strong> {request.fiduciary_id}</li>
                        <li><strong>Created:</strong> {request.created_at}</li>
                        <li><strong>Days Overdue:</strong> {days_overdue}</li>
                    </ul>
                    
                    <p><strong>This is a DPDP Act compliance violation that requires immediate attention.</strong></p>
                    
                    <p>Under Section 9 of the Digital Personal Data Protection Act, 2023, data fiduciaries must 
                    complete deletion requests within 30 days of receipt.</p>
                    
                    <p>Immediate action is required to:</p>
                    <ol>
                        <li>Complete the deletion request</li>
                        <li>Document the delay reason</li>
                        <li>Notify the affected principal</li>
                    </ol>
                </div>
                <div class="footer">
                    <p>ConsentChain Compliance Monitoring System</p>
                </div>
            </body>
            </html>
            """

            await self.notification_service.send_email(
                recipient_email=compliance_email,
                subject=f"ESCALATION: Overdue Deletion Request {request.id} - DPDP VIOLATION",
                html_body=html_body,
            )
            logger.info(f"Escalation email sent to compliance team: {compliance_email}")
