import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from uuid import UUID, uuid4
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, and_, or_
from sqlalchemy.dialects.postgresql import insert

from api.database import (
    DataPrincipalDB,
    DataFiduciaryDB,
    ConsentRecordDB,
    ConsentEventDB,
    AuditLogDB,
    MerkleRootDB,
    ComplianceReportDB,
    ConsentStatusDB,
    EventTypeDB,
)
from core.crypto import CryptoUtils, MerkleTree, DPDPComplianceValidator
from core.constants import (
    CONSENT_GRANTED,
    CONSENT_REVOKED,
    CONSENT_MODIFIED,
    EVENT_TYPE_CONSENT_GRANTED,
    EVENT_TYPE_CONSENT_REVOKED,
    EVENT_TYPE_CONSENT_MODIFIED,
)
from contracts.client import AlgorandClient, ConsentContractClient, AuditTrailClient


class ConsentService:
    def __init__(
        self,
        session: AsyncSession,
        algorand_client: AlgorandClient,
        consent_app_id: int,
        audit_app_id: int,
    ):
        self.session = session
        self.consent_client = ConsentContractClient(algorand_client, consent_app_id)
        self.audit_client = AuditTrailClient(algorand_client, audit_app_id)

    async def register_principal(
        self,
        wallet_address: str,
        email: str,
        phone: Optional[str] = None,
    ) -> DataPrincipalDB:
        existing = await self.session.execute(
            select(DataPrincipalDB).where(DataPrincipalDB.wallet_address == wallet_address)
        )
        if existing.scalar_one_or_none():
            raise ValueError("Principal already registered")

        principal = DataPrincipalDB(
            wallet_address=wallet_address,
            email_hash=CryptoUtils.hash_email(email),
            phone_hash=CryptoUtils.hash_phone(phone) if phone else None,
        )
        self.session.add(principal)
        await self.session.commit()
        return principal

    async def register_fiduciary(
        self,
        name: str,
        registration_number: str,
        wallet_address: str,
        contact_email: str,
        data_categories: List[str],
        purposes: List[str],
    ) -> tuple[DataFiduciaryDB, str]:
        existing = await self.session.execute(
            select(DataFiduciaryDB).where(
                DataFiduciaryDB.registration_number == registration_number
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError("Fiduciary already registered")

        api_key = CryptoUtils.generate_api_key()
        api_key_hash = CryptoUtils.hash_api_key(api_key)

        fiduciary = DataFiduciaryDB(
            name=name,
            registration_number=registration_number,
            wallet_address=wallet_address,
            contact_email=contact_email,
            api_key_hash=api_key_hash,
            data_categories=json.dumps(data_categories),
            purposes=json.dumps(purposes),
        )
        self.session.add(fiduciary)
        await self.session.commit()

        return fiduciary, api_key

    async def create_consent(
        self,
        principal_wallet: str,
        fiduciary_id: UUID,
        purpose: str,
        data_types: List[str],
        duration_days: int,
        metadata: Optional[Dict] = None,
        signature: Optional[str] = None,
    ) -> ConsentRecordDB:
        is_valid, violations = DPDPComplianceValidator.validate_consent_purpose(purpose, data_types)
        if not is_valid:
            raise ValueError(f"Compliance violation: {violations}")

        is_valid, error = DPDPComplianceValidator.validate_consent_duration(duration_days, purpose)
        if not is_valid:
            raise ValueError(f"Invalid duration: {error}")

        principal = await self.session.execute(
            select(DataPrincipalDB).where(DataPrincipalDB.wallet_address == principal_wallet)
        )
        principal = principal.scalar_one_or_none()
        if not principal:
            principal = DataPrincipalDB(wallet_address=principal_wallet)
            self.session.add(principal)
            await self.session.flush()

        fiduciary = await self.session.get(DataFiduciaryDB, fiduciary_id)
        if not fiduciary:
            raise ValueError("Fiduciary not found")

        now = datetime.utcnow()
        expires_at = now + timedelta(days=duration_days)

        consent_hash = CryptoUtils.generate_consent_hash(
            principal_id=str(principal.id),
            fiduciary_id=str(fiduciary.id),
            purpose=purpose,
            data_types=data_types,
            timestamp=now,
        )

        data_types_hash = CryptoUtils.sha256(json.dumps(sorted(data_types)))

        tx_id = await asyncio.to_thread(
            self.consent_client.register_consent,
            principal_wallet,
            fiduciary.wallet_address,
            purpose,
            data_types_hash,
            consent_hash,
            int(expires_at.timestamp()),
        )

        consent = ConsentRecordDB(
            principal_id=principal.id,
            fiduciary_id=fiduciary.id,
            purpose=purpose,
            data_types=json.dumps(data_types),
            status=ConsentStatusDB.GRANTED,
            granted_at=now,
            expires_at=expires_at,
            on_chain_tx_id=tx_id,
            on_chain_app_id=self.consent_client.app_id,
            consent_hash=consent_hash,
            metadata=json.dumps(metadata) if metadata else None,
        )
        self.session.add(consent)
        await self.session.flush()

        event = await self._create_event(
            consent_id=consent.id,
            event_type=EventTypeDB.CONSENT_GRANTED,
            actor=principal_wallet,
            actor_type="principal",
            previous_status=None,
            new_status=ConsentStatusDB.GRANTED,
            tx_id=tx_id,
            signature=signature,
        )

        await self._log_audit(
            principal_id=principal.id,
            fiduciary_id=fiduciary.id,
            action="CONSENT_CREATED",
            resource_type="consent",
            resource_id=consent.id,
            on_chain_reference=tx_id,
        )

        await self.session.commit()
        return consent

    async def revoke_consent(
        self,
        consent_id: UUID,
        reason: Optional[str] = None,
        signature: Optional[str] = None,
    ) -> ConsentRecordDB:
        consent = await self.session.get(ConsentRecordDB, consent_id)
        if not consent:
            raise ValueError("Consent not found")

        if consent.status == ConsentStatusDB.REVOKED:
            raise ValueError("Consent already revoked")

        principal = await self.session.get(DataPrincipalDB, consent.principal_id)

        tx_id = await asyncio.to_thread(
            self.consent_client.revoke_consent,
            principal.wallet_address,
        )

        previous_status = consent.status
        consent.status = ConsentStatusDB.REVOKED
        consent.revoked_at = datetime.utcnow()
        consent.on_chain_tx_id = tx_id

        event = await self._create_event(
            consent_id=consent.id,
            event_type=EventTypeDB.CONSENT_REVOKED,
            actor=principal.wallet_address,
            actor_type="principal",
            previous_status=previous_status,
            new_status=ConsentStatusDB.REVOKED,
            tx_id=tx_id,
            metadata={"reason": reason} if reason else None,
            signature=signature,
        )

        await self._log_audit(
            principal_id=principal.id,
            fiduciary_id=consent.fiduciary_id,
            action="CONSENT_REVOKED",
            resource_type="consent",
            resource_id=consent.id,
            on_chain_reference=tx_id,
        )

        await self.session.commit()
        return consent

    async def modify_consent(
        self,
        consent_id: UUID,
        new_purpose: Optional[str] = None,
        new_data_types: Optional[List[str]] = None,
        new_duration_days: Optional[int] = None,
        reason: Optional[str] = None,
        signature: Optional[str] = None,
    ) -> ConsentRecordDB:
        consent = await self.session.get(ConsentRecordDB, consent_id)
        if not consent:
            raise ValueError("Consent not found")

        if consent.status == ConsentStatusDB.REVOKED:
            raise ValueError("Cannot modify revoked consent")

        principal = await self.session.get(DataPrincipalDB, consent.principal_id)
        previous_status = consent.status

        if new_purpose:
            consent.purpose = new_purpose
        if new_data_types:
            consent.data_types = json.dumps(new_data_types)
        if new_duration_days:
            consent.expires_at = datetime.utcnow() + timedelta(days=new_duration_days)

        consent.status = ConsentStatusDB.MODIFIED
        consent.updated_at = datetime.utcnow()

        new_hash = CryptoUtils.generate_consent_hash(
            principal_id=str(consent.principal_id),
            fiduciary_id=str(consent.fiduciary_id),
            purpose=consent.purpose,
            data_types=json.loads(consent.data_types),
            timestamp=datetime.utcnow(),
        )
        consent.consent_hash = new_hash

        event = await self._create_event(
            consent_id=consent.id,
            event_type=EventTypeDB.CONSENT_MODIFIED,
            actor=principal.wallet_address,
            actor_type="principal",
            previous_status=previous_status,
            new_status=ConsentStatusDB.MODIFIED,
            metadata={
                "reason": reason,
                "changes": {
                    "new_purpose": new_purpose,
                    "new_data_types": new_data_types,
                    "new_duration_days": new_duration_days,
                },
            },
            signature=signature,
        )

        await self._log_audit(
            principal_id=principal.id,
            fiduciary_id=consent.fiduciary_id,
            action="CONSENT_MODIFIED",
            resource_type="consent",
            resource_id=consent.id,
        )

        await self.session.commit()
        return consent

    async def verify_consent(
        self,
        consent_id: UUID,
        verifier_wallet: Optional[str] = None,
    ) -> Dict[str, Any]:
        consent = await self.session.get(ConsentRecordDB, consent_id)
        if not consent:
            return {"valid": False, "reason": "Consent not found"}

        if consent.status == ConsentStatusDB.REVOKED:
            return {
                "valid": False,
                "reason": "Consent revoked",
                "revoked_at": consent.revoked_at.isoformat(),
            }

        if consent.status == ConsentStatusDB.EXPIRED:
            return {
                "valid": False,
                "reason": "Consent expired",
                "expired_at": consent.expires_at.isoformat(),
            }

        if consent.expires_at and consent.expires_at < datetime.utcnow():
            consent.status = ConsentStatusDB.EXPIRED
            await self.session.commit()
            return {
                "valid": False,
                "reason": "Consent expired",
                "expired_at": consent.expires_at.isoformat(),
            }

        return {
            "valid": True,
            "consent_id": str(consent.id),
            "principal_id": str(consent.principal_id),
            "fiduciary_id": str(consent.fiduciary_id),
            "purpose": consent.purpose,
            "data_types": json.loads(consent.data_types),
            "granted_at": consent.granted_at.isoformat(),
            "expires_at": consent.expires_at.isoformat() if consent.expires_at else None,
            "on_chain_tx_id": consent.on_chain_tx_id,
            "consent_hash": consent.consent_hash,
        }

    async def query_consents(
        self,
        principal_id: Optional[UUID] = None,
        fiduciary_id: Optional[UUID] = None,
        status: Optional[str] = None,
        purpose: Optional[str] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        page: int = 1,
        limit: int = 20,
    ) -> List[ConsentRecordDB]:
        query = select(ConsentRecordDB)

        conditions = []
        if principal_id:
            conditions.append(ConsentRecordDB.principal_id == principal_id)
        if fiduciary_id:
            conditions.append(ConsentRecordDB.fiduciary_id == fiduciary_id)
        if status:
            conditions.append(ConsentRecordDB.status == ConsentStatusDB(status))
        if purpose:
            conditions.append(ConsentRecordDB.purpose == purpose)
        if from_date:
            conditions.append(ConsentRecordDB.created_at >= from_date)
        if to_date:
            conditions.append(ConsentRecordDB.created_at <= to_date)

        if conditions:
            query = query.where(and_(*conditions))

        query = query.order_by(ConsentRecordDB.created_at.desc())
        query = query.offset((page - 1) * limit).limit(limit)

        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_consent_history(self, consent_id: UUID) -> List[ConsentEventDB]:
        result = await self.session.execute(
            select(ConsentEventDB)
            .where(ConsentEventDB.consent_id == consent_id)
            .order_by(ConsentEventDB.created_at)
        )
        return result.scalars().all()

    async def _create_event(
        self,
        consent_id: UUID,
        event_type: EventTypeDB,
        actor: str,
        actor_type: str,
        previous_status: Optional[ConsentStatusDB],
        new_status: ConsentStatusDB,
        tx_id: Optional[str] = None,
        block_number: Optional[int] = None,
        ipfs_hash: Optional[str] = None,
        metadata: Optional[Dict] = None,
        signature: Optional[str] = None,
    ) -> ConsentEventDB:
        event = ConsentEventDB(
            consent_id=consent_id,
            event_type=event_type,
            actor=actor,
            actor_type=actor_type,
            previous_status=previous_status,
            new_status=new_status,
            tx_id=tx_id,
            block_number=block_number,
            ipfs_hash=ipfs_hash,
            metadata=json.dumps(metadata) if metadata else None,
            signature=signature,
        )
        self.session.add(event)
        return event

    async def _log_audit(
        self,
        principal_id: Optional[UUID],
        fiduciary_id: Optional[UUID],
        action: str,
        resource_type: str,
        resource_id: UUID,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        on_chain_reference: Optional[str] = None,
    ) -> AuditLogDB:
        audit = AuditLogDB(
            principal_id=principal_id,
            fiduciary_id=fiduciary_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent,
            on_chain_reference=on_chain_reference,
        )
        self.session.add(audit)
        return audit


class AuditService:
    def __init__(
        self,
        session: AsyncSession,
        audit_client: AuditTrailClient,
    ):
        self.session = session
        self.audit_client = audit_client

    async def get_audit_trail(
        self,
        principal_id: Optional[UUID] = None,
        fiduciary_id: Optional[UUID] = None,
        consent_id: Optional[UUID] = None,
        event_type: Optional[str] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        page: int = 1,
        limit: int = 50,
    ) -> List[AuditLogDB]:
        query = select(AuditLogDB)

        conditions = []
        if principal_id:
            conditions.append(AuditLogDB.principal_id == principal_id)
        if fiduciary_id:
            conditions.append(AuditLogDB.fiduciary_id == fiduciary_id)
        if event_type:
            conditions.append(AuditLogDB.action == event_type)
        if from_date:
            conditions.append(AuditLogDB.created_at >= from_date)
        if to_date:
            conditions.append(AuditLogDB.created_at <= to_date)

        if conditions:
            query = query.where(and_(*conditions))

        query = query.order_by(AuditLogDB.created_at.desc())
        query = query.offset((page - 1) * limit).limit(limit)

        result = await self.session.execute(query)
        return result.scalars().all()

    async def generate_merkle_root(
        self,
        event_ids: List[UUID],
    ) -> tuple[str, str]:
        events = []
        for event_id in event_ids:
            event = await self.session.get(ConsentEventDB, event_id)
            if event:
                events.append(event)

        leaves = [
            CryptoUtils.sha256(f"{e.id}:{e.event_type.value}:{e.created_at.isoformat()}")
            for e in events
        ]

        merkle_tree = MerkleTree(leaves)
        merkle_root = merkle_tree.root

        tx_id = await asyncio.to_thread(
            self.audit_client.batch_log_events,
            merkle_root,
            len(events),
            leaves[-1] if leaves else "0" * 64,
        )

        merkle_root_record = MerkleRootDB(
            root_hash=merkle_root,
            event_count=len(events),
            first_event_id=event_ids[0] if event_ids else None,
            last_event_id=event_ids[-1] if event_ids else None,
            on_chain_tx_id=tx_id,
        )
        self.session.add(merkle_root_record)
        await self.session.commit()

        return merkle_root, tx_id

    async def verify_audit_integrity(
        self,
        audit_log_id: UUID,
    ) -> Dict[str, Any]:
        audit_log = await self.session.get(AuditLogDB, audit_log_id)
        if not audit_log:
            return {"valid": False, "reason": "Audit log not found"}

        if audit_log.on_chain_reference:
            return {"valid": True, "on_chain_reference": audit_log.on_chain_reference}

        return {"valid": True, "reason": "Audit log exists in database"}


class ComplianceService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def generate_compliance_report(
        self,
        fiduciary_id: UUID,
        period_start: datetime,
        period_end: datetime,
    ) -> ComplianceReportDB:
        consents = await self.session.execute(
            select(ConsentRecordDB).where(
                and_(
                    ConsentRecordDB.fiduciary_id == fiduciary_id,
                    ConsentRecordDB.created_at >= period_start,
                    ConsentRecordDB.created_at <= period_end,
                )
            )
        )
        consents = consents.scalars().all()

        total = len(consents)
        active = sum(1 for c in consents if c.status == ConsentStatusDB.GRANTED)
        revoked = sum(1 for c in consents if c.status == ConsentStatusDB.REVOKED)
        expired = sum(1 for c in consents if c.status == ConsentStatusDB.EXPIRED)

        sensitive_count = sum(
            1
            for c in consents
            if any(
                dt in DPDPComplianceValidator.SENSITIVE_DATA_TYPES
                for dt in json.loads(c.data_types)
            )
        )

        third_party_count = sum(1 for c in consents if c.purpose == "THIRD_PARTY_SHARING")

        audit_events = await self.session.execute(
            select(AuditLogDB).where(
                and_(
                    AuditLogDB.fiduciary_id == fiduciary_id,
                    AuditLogDB.created_at >= period_start,
                    AuditLogDB.created_at <= period_end,
                )
            )
        )
        audit_count = len(audit_events.scalars().all())

        compliance_score = self._calculate_compliance_score(
            total=total,
            active=active,
            revoked=revoked,
            expired=expired,
            sensitive_count=sensitive_count,
            audit_count=audit_count,
        )

        report = ComplianceReportDB(
            fiduciary_id=fiduciary_id,
            period_start=period_start,
            period_end=period_end,
            total_consents=total,
            active_consents=active,
            revoked_consents=revoked,
            expired_consents=expired,
            sensitive_data_consents=sensitive_count,
            third_party_sharing_count=third_party_count,
            audit_events=audit_count,
            compliance_score=compliance_score,
        )
        self.session.add(report)
        await self.session.commit()

        return report

    def _calculate_compliance_score(
        self,
        total: int,
        active: int,
        revoked: int,
        expired: int,
        sensitive_count: int,
        audit_count: int,
    ) -> int:
        if total == 0:
            return 100

        score = 100

        revoked_ratio = revoked / total
        if revoked_ratio > 0.3:
            score -= min(20, int(revoked_ratio * 50))

        if audit_count < total * 0.5:
            score -= 10

        if sensitive_count > 0:
            score += 5

        return max(0, min(100, score))

    async def get_fiduciary_compliance_status(
        self,
        fiduciary_id: UUID,
    ) -> Dict[str, Any]:
        latest_report = await self.session.execute(
            select(ComplianceReportDB)
            .where(ComplianceReportDB.fiduciary_id == fiduciary_id)
            .order_by(ComplianceReportDB.created_at.desc())
            .limit(1)
        )
        latest_report = latest_report.scalar_one_or_none()

        checklist = DPDPComplianceValidator.generate_compliance_checklist({})

        return {
            "fiduciary_id": str(fiduciary_id),
            "compliance_score": latest_report.compliance_score if latest_report else None,
            "last_report_date": latest_report.created_at.isoformat() if latest_report else None,
            "compliance_checklist": checklist,
        }
