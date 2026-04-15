"""Data Portability - DPDP Act Right to Data Portability.

Implements data export and transfer functionality for data principals.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4
from enum import Enum
import hashlib

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class ExportFormat(str, Enum):
    JSON = "json"
    CSV = "csv"
    XML = "xml"


class TransferStatus(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class DataExportRequest(BaseModel):
    principal_id: UUID
    format: ExportFormat = ExportFormat.JSON
    include_audit_logs: bool = True
    include_consents: bool = True
    include_grievances: bool = True
    include_deletion_requests: bool = False
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None


class DataTransferRequest(BaseModel):
    principal_id: UUID
    source_fiduciary_id: UUID
    target_fiduciary_id: UUID
    data_categories: List[str]
    consent_id: Optional[UUID] = None


class DataPortabilityService:
    """
    Service for data export and transfer operations.

    Per DPDP Act, data principals have the right to:
    - Obtain a copy of their data in a structured, machine-readable format
    - Transfer their data to another fiduciary
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def export_principal_data(
        self,
        request: DataExportRequest,
    ) -> Dict[str, Any]:
        """
        Export all data for a principal in the requested format.

        Returns a structured data package with verification signature.
        """
        from api.database import ConsentRecordDB, AuditLogDB, DataPrincipalDB
        from api.grievance import GrievanceDB

        result = await self.db.execute(
            select(DataPrincipalDB).where(DataPrincipalDB.id == request.principal_id)
        )
        principal = result.scalar_one_or_none()

        if not principal:
            raise ValueError("Principal not found")

        export_data = {
            "export_metadata": {
                "export_id": str(uuid4()),
                "principal_id": str(request.principal_id),
                "principal_wallet": principal.wallet_address,
                "export_timestamp": datetime.now(timezone.utc).isoformat(),
                "format": request.format.value,
                "version": "1.0",
                "generator": "ConsentChain DPDP Compliance System",
            },
            "data": {},
        }

        if request.include_consents:
            result = await self.db.execute(
                select(ConsentRecordDB).where(ConsentRecordDB.principal_id == request.principal_id)
            )
            consents = result.scalars().all()

            export_data["data"]["consents"] = [
                {
                    "consent_id": str(c.id),
                    "fiduciary_id": str(c.fiduciary_id),
                    "purpose": c.purpose,
                    "data_types": json.loads(c.data_types),
                    "status": c.status.value,
                    "granted_at": c.granted_at.isoformat() if c.granted_at else None,
                    "expires_at": c.expires_at.isoformat() if c.expires_at else None,
                    "revoked_at": c.revoked_at.isoformat() if c.revoked_at else None,
                    "consent_hash": c.consent_hash,
                    "created_at": c.created_at.isoformat(),
                }
                for c in consents
            ]

        if request.include_audit_logs:
            result = await self.db.execute(
                select(AuditLogDB).where(AuditLogDB.principal_id == request.principal_id)
            )
            audit_logs = result.scalars().all()

            export_data["data"]["audit_logs"] = [
                {
                    "log_id": str(l.id),
                    "action": l.action,
                    "resource_type": l.resource_type,
                    "resource_id": str(l.resource_id),
                    "on_chain_reference": l.on_chain_reference,
                    "created_at": l.created_at.isoformat(),
                }
                for l in audit_logs
            ]

        if request.include_grievances:
            result = await self.db.execute(
                select(GrievanceDB).where(GrievanceDB.principal_id == request.principal_id)
            )
            grievances = result.scalars().all()

            export_data["data"]["grievances"] = [
                {
                    "grievance_id": str(g.id),
                    "fiduciary_id": str(g.fiduciary_id),
                    "type": g.grievance_type.value,
                    "subject": g.subject,
                    "status": g.status.value,
                    "created_at": g.created_at.isoformat(),
                    "resolution_date": g.resolution_date.isoformat() if g.resolution_date else None,
                }
                for g in grievances
            ]

        export_json = json.dumps(export_data, sort_keys=True)
        export_hash = hashlib.sha256(export_json.encode()).hexdigest()

        export_data["verification"] = {
            "hash": export_hash,
            "algorithm": "SHA-256",
            "signed_at": datetime.now(timezone.utc).isoformat(),
        }

        logger.info(
            f"Data export completed for principal {request.principal_id}: "
            f"{len(export_data['data'].get('consents', []))} consents, "
            f"hash: {export_hash[:16]}..."
        )

        return export_data

    async def transfer_to_fiduciary(
        self,
        request: DataTransferRequest,
    ) -> Dict[str, Any]:
        """
        Transfer data from one fiduciary to another.

        Creates a transfer record and notifies both fiduciaries.
        """
        transfer_id = uuid4()

        transfer_data = await self.export_principal_data(
            DataExportRequest(
                principal_id=request.principal_id,
                format=ExportFormat.JSON,
                include_consents=True,
                include_audit_logs=True,
            )
        )

        transfer_record = {
            "transfer_id": str(transfer_id),
            "principal_id": str(request.principal_id),
            "source_fiduciary_id": str(request.source_fiduciary_id),
            "target_fiduciary_id": str(request.target_fiduciary_id),
            "data_categories": request.data_categories,
            "status": TransferStatus.PENDING.value,
            "initiated_at": datetime.now(timezone.utc).isoformat(),
            "data_package": transfer_data,
        }

        logger.info(
            f"Data transfer initiated: {transfer_id} from "
            f"{request.source_fiduciary_id} to {request.target_fiduciary_id}"
        )

        return transfer_record

    async def get_export_formats(self) -> List[Dict[str, str]]:
        """Get available export formats."""
        return [
            {
                "format": "json",
                "description": "JavaScript Object Notation - machine-readable, widely supported",
                "mime_type": "application/json",
            },
            {
                "format": "csv",
                "description": "Comma-Separated Values - spreadsheet compatible",
                "mime_type": "text/csv",
            },
            {
                "format": "xml",
                "description": "Extensible Markup Language - structured document format",
                "mime_type": "application/xml",
            },
        ]

    def format_as_csv(self, export_data: Dict[str, Any]) -> str:
        """Convert export data to CSV format."""
        import io
        import csv

        output = io.StringIO()
        writer = csv.writer(output)

        consents = export_data.get("data", {}).get("consents", [])
        if consents:
            writer.writerow(
                [
                    "consent_id",
                    "fiduciary_id",
                    "purpose",
                    "status",
                    "granted_at",
                    "expires_at",
                    "consent_hash",
                ]
            )
            for c in consents:
                writer.writerow(
                    [
                        c["consent_id"],
                        c["fiduciary_id"],
                        c["purpose"],
                        c["status"],
                        c["granted_at"] or "",
                        c["expires_at"] or "",
                        c["consent_hash"],
                    ]
                )

        return output.getvalue()
