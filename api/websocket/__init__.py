from fastapi import WebSocket, WebSocketDisconnect, Depends, Query
from typing import Dict, Set, Optional, List, Any
from datetime import datetime, timezone
import json
import asyncio
import logging
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict

logger = logging.getLogger(__name__)


class WSMessageType(str, Enum):
    CONSENT_GRANTED = "consent_granted"
    CONSENT_REVOKED = "consent_revoked"
    CONSENT_MODIFIED = "consent_modified"
    CONSENT_EXPIRING = "consent_expiring"
    CONSENT_EXPIRED = "consent_expired"
    DATA_ACCESS = "data_access"
    DELETION_REQUEST = "deletion_request"
    DELETION_COMPLETED = "deletion_completed"
    BREACH_NOTIFICATION = "breach_notification"
    COMPLIANCE_ALERT = "compliance_alert"
    SYSTEM_ANNOUNCEMENT = "system_announcement"
    PING = "ping"
    PONG = "pong"


@dataclass
class WSMessage:
    type: WSMessageType
    data: Dict[str, Any]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    principal_id: Optional[str] = None
    fiduciary_id: Optional[str] = None

    def to_json(self) -> str:
        return json.dumps(
            {
                "type": self.type.value,
                "data": self.data,
                "timestamp": self.timestamp.isoformat(),
                "principal_id": self.principal_id,
                "fiduciary_id": self.fiduciary_id,
            }
        )


class ConnectionManager:
    def __init__(self):
        self._principal_connections: Dict[str, Set[WebSocket]] = defaultdict(set)
        self._fiduciary_connections: Dict[str, Set[WebSocket]] = defaultdict(set)
        self._admin_connections: Set[WebSocket] = set()
        self._all_connections: Set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(
        self,
        websocket: WebSocket,
        principal_id: Optional[str] = None,
        fiduciary_id: Optional[str] = None,
        is_admin: bool = False,
    ):
        await websocket.accept()
        async with self._lock:
            self._all_connections.add(websocket)
            if principal_id:
                self._principal_connections[principal_id].add(websocket)
            if fiduciary_id:
                self._fiduciary_connections[fiduciary_id].add(websocket)
            if is_admin:
                self._admin_connections.add(websocket)
        logger.info(f"WebSocket connected: principal={principal_id}, fiduciary={fiduciary_id}")

    async def disconnect(
        self,
        websocket: WebSocket,
        principal_id: Optional[str] = None,
        fiduciary_id: Optional[str] = None,
        is_admin: bool = False,
    ):
        async with self._lock:
            self._all_connections.discard(websocket)
            if principal_id:
                self._principal_connections[principal_id].discard(websocket)
            if fiduciary_id:
                self._fiduciary_connections[fiduciary_id].discard(websocket)
            if is_admin:
                self._admin_connections.discard(websocket)
        logger.info(f"WebSocket disconnected: principal={principal_id}, fiduciary={fiduciary_id}")

    async def send_personal(self, websocket: WebSocket, message: WSMessage):
        try:
            await websocket.send_text(message.to_json())
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")

    async def broadcast_to_principal(self, principal_id: str, message: WSMessage):
        connections = self._principal_connections.get(principal_id, set()).copy()
        message.principal_id = principal_id
        for connection in connections:
            try:
                await connection.send_text(message.to_json())
            except Exception:
                pass

    async def broadcast_to_fiduciary(self, fiduciary_id: str, message: WSMessage):
        connections = self._fiduciary_connections.get(fiduciary_id, set()).copy()
        message.fiduciary_id = fiduciary_id
        for connection in connections:
            try:
                await connection.send_text(message.to_json())
            except Exception:
                pass

    async def broadcast_to_admins(self, message: WSMessage):
        for connection in self._admin_connections.copy():
            try:
                await connection.send_text(message.to_json())
            except Exception:
                pass

    async def broadcast_all(self, message: WSMessage):
        for connection in self._all_connections.copy():
            try:
                await connection.send_text(message.to_json())
            except Exception:
                pass

    async def broadcast_consent_event(
        self,
        event_type: WSMessageType,
        consent_id: str,
        principal_id: str,
        fiduciary_id: str,
        additional_data: Optional[Dict[str, Any]] = None,
    ):
        message = WSMessage(
            type=event_type,
            data={
                "consent_id": consent_id,
                "event": event_type.value,
                **(additional_data or {}),
            },
            principal_id=principal_id,
            fiduciary_id=fiduciary_id,
        )
        await self.broadcast_to_principal(principal_id, message)
        await self.broadcast_to_fiduciary(fiduciary_id, message)

    def get_connection_count(self) -> Dict[str, int]:
        return {
            "total": len(self._all_connections),
            "principals": len(self._principal_connections),
            "fiduciaries": len(self._fiduciary_connections),
            "admins": len(self._admin_connections),
        }


manager = ConnectionManager()


class WebSocketHandler:
    def __init__(self, manager: ConnectionManager):
        self.manager = manager

    async def handle_message(self, websocket: WebSocket, data: str):
        try:
            message = json.loads(data)
            msg_type = message.get("type")

            if msg_type == WSMessageType.PING.value:
                await self.manager.send_personal(
                    websocket, WSMessage(type=WSMessageType.PONG, data={})
                )
            elif msg_type == "subscribe":
                pass
            else:
                logger.warning(f"Unknown WebSocket message type: {msg_type}")
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON received: {data}")

    async def listen(
        self,
        websocket: WebSocket,
        principal_id: Optional[str] = None,
        fiduciary_id: Optional[str] = None,
        is_admin: bool = False,
    ):
        await self.manager.connect(websocket, principal_id, fiduciary_id, is_admin)
        try:
            while True:
                data = await websocket.receive_text()
                await self.handle_message(websocket, data)
        except WebSocketDisconnect:
            await self.manager.disconnect(websocket, principal_id, fiduciary_id, is_admin)
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
            await self.manager.disconnect(websocket, principal_id, fiduciary_id, is_admin)


ws_handler = WebSocketHandler(manager)


async def notify_consent_granted(
    consent_id: str,
    principal_id: str,
    fiduciary_id: str,
    purpose: str,
    data_types: List[str],
    expires_at: Optional[datetime] = None,
):
    await manager.broadcast_consent_event(
        WSMessageType.CONSENT_GRANTED,
        consent_id,
        principal_id,
        fiduciary_id,
        {
            "purpose": purpose,
            "data_types": data_types,
            "expires_at": expires_at.isoformat() if expires_at else None,
        },
    )


async def notify_consent_revoked(
    consent_id: str,
    principal_id: str,
    fiduciary_id: str,
    reason: Optional[str] = None,
):
    await manager.broadcast_consent_event(
        WSMessageType.CONSENT_REVOKED,
        consent_id,
        principal_id,
        fiduciary_id,
        {"reason": reason},
    )


async def notify_consent_modified(
    consent_id: str,
    principal_id: str,
    fiduciary_id: str,
    changes: Dict[str, Any],
):
    await manager.broadcast_consent_event(
        WSMessageType.CONSENT_MODIFIED,
        consent_id,
        principal_id,
        fiduciary_id,
        {"changes": changes},
    )


async def notify_consent_expiring(
    consent_id: str,
    principal_id: str,
    fiduciary_id: str,
    days_remaining: int,
):
    await manager.broadcast_consent_event(
        WSMessageType.CONSENT_EXPIRING,
        consent_id,
        principal_id,
        fiduciary_id,
        {"days_remaining": days_remaining},
    )


async def notify_breach(
    fiduciary_id: str,
    breach_id: str,
    severity: str,
    affected_principals: List[str],
):
    message = WSMessage(
        type=WSMessageType.BREACH_NOTIFICATION,
        data={
            "breach_id": breach_id,
            "severity": severity,
            "affected_count": len(affected_principals),
        },
        fiduciary_id=fiduciary_id,
    )
    await manager.broadcast_to_fiduciary(fiduciary_id, message)
    for principal_id in affected_principals:
        await manager.broadcast_to_principal(principal_id, message)


async def notify_deletion_request(
    principal_id: str,
    fiduciary_id: str,
    request_id: str,
    deadline: datetime,
):
    message = WSMessage(
        type=WSMessageType.DELETION_REQUEST,
        data={
            "request_id": request_id,
            "deadline": deadline.isoformat(),
        },
        principal_id=principal_id,
        fiduciary_id=fiduciary_id,
    )
    await manager.broadcast_to_principal(principal_id, message)
    await manager.broadcast_to_fiduciary(fiduciary_id, message)
