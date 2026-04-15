"""IPFS integration for ConsentChain - stores consent evidence off-chain."""

import hashlib
import json
from typing import Optional, Any
from dataclasses import dataclass
from datetime import datetime, timezone
import httpx


@dataclass
class IPFSConfig:
    api_url: str = "https://ipfs.infura.io:5001"
    gateway_url: str = "https://ipfs.io/ipfs"
    project_id: Optional[str] = None
    project_secret: Optional[str] = None
    timeout: int = 30


@dataclass
class IPFSUploadResult:
    cid: str
    size: int
    url: str
    uploaded_at: datetime


class IPFSClient:
    def __init__(self, config: Optional[IPFSConfig] = None):
        self.config = config or IPFSConfig()
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            headers = {}
            if self.config.project_id and self.config.project_secret:
                import base64

                auth = base64.b64encode(
                    f"{self.config.project_id}:{self.config.project_secret}".encode()
                ).decode()
                headers["Authorization"] = f"Basic {auth}"

            self._client = httpx.AsyncClient(
                base_url=self.config.api_url,
                headers=headers,
                timeout=self.config.timeout,
            )
        return self._client

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None

    async def upload_json(self, data: dict) -> IPFSUploadResult:
        client = await self._get_client()

        json_data = json.dumps(data, default=str)
        files = {"file": ("consent.json", json_data.encode(), "application/json")}

        response = await client.post("/api/v0/add", files=files)
        response.raise_for_status()

        result = response.json()
        cid = result["Hash"]
        size = result["Size"]

        pinned = await self.pin_cid(cid)
        if not pinned:
            import logging

            logging.getLogger(__name__).warning(f"Failed to pin CID {cid}")

        return IPFSUploadResult(
            cid=cid,
            size=size,
            url=f"{self.config.gateway_url}/{cid}",
            uploaded_at=datetime.now(timezone.utc),
        )

    async def upload_bytes(self, data: bytes, filename: str = "data") -> IPFSUploadResult:
        client = await self._get_client()

        files = {"file": (filename, data)}
        response = await client.post("/api/v0/add", files=files)
        response.raise_for_status()

        result = response.json()
        cid = result["Hash"]
        size = result["Size"]

        pinned = await self.pin_cid(cid)
        if not pinned:
            import logging

            logging.getLogger(__name__).warning(f"Failed to pin CID {cid}")

        return IPFSUploadResult(
            cid=cid,
            size=size,
            url=f"{self.config.gateway_url}/{cid}",
            uploaded_at=datetime.now(timezone.utc),
        )

    async def get_json(self, cid: str) -> dict:
        gateway_url = f"{self.config.gateway_url}/{cid}"

        async with httpx.AsyncClient() as client:
            response = await client.get(gateway_url)
            response.raise_for_status()
            return response.json()

    async def pin_cid(self, cid: str) -> bool:
        import logging

        logger = logging.getLogger(__name__)

        client = await self._get_client()

        try:
            response = await client.post("/api/v0/pin/add", params={"arg": cid})
            if response.status_code != 200:
                logger.error(f"Failed to pin {cid}: HTTP {response.status_code}")
                return False

            verify_response = await client.post("/api/v0/pin/ls", params={"arg": cid})
            if verify_response.status_code == 200:
                verify_data = verify_response.json()
                if "Keys" in verify_data and cid in verify_data["Keys"]:
                    logger.info(f"Successfully pinned and verified CID: {cid}")
                    return True
                else:
                    logger.warning(f"Pin verification failed for {cid}")
                    return False
            else:
                logger.warning(f"Pin verification request failed for {cid}")
                return True

        except Exception as e:
            logger.error(f"Error pinning CID {cid}: {e}")
            return False

    async def unpin_cid(self, cid: str) -> bool:
        import logging

        logger = logging.getLogger(__name__)

        client = await self._get_client()
        try:
            response = await client.post("/api/v0/pin/rm", params={"arg": cid})
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Error unpinning CID {cid}: {e}")
            return False


class ConsentEvidenceStore:
    def __init__(self, ipfs_client: Optional[IPFSClient] = None):
        self.ipfs = ipfs_client or IPFSClient()

    async def store_consent_evidence(
        self,
        consent_id: str,
        principal_wallet: str,
        fiduciary_wallet: str,
        purpose: str,
        data_types: list[str],
        granted_at: datetime,
        expires_at: Optional[datetime],
        signature: str,
        tx_id: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> IPFSUploadResult:
        evidence = {
            "version": "1.0",
            "consent_id": consent_id,
            "principal_wallet": principal_wallet,
            "fiduciary_wallet": fiduciary_wallet,
            "purpose": purpose,
            "data_types": data_types,
            "granted_at": granted_at.isoformat(),
            "expires_at": expires_at.isoformat() if expires_at else None,
            "signature": signature,
            "tx_id": tx_id,
            "metadata": metadata or {},
            "content_hash": self._compute_hash(
                consent_id, principal_wallet, fiduciary_wallet, purpose, granted_at
            ),
        }

        return await self.ipfs.upload_json(evidence)

    async def store_revocation_evidence(
        self,
        consent_id: str,
        revoked_at: datetime,
        revoked_by: str,
        reason: Optional[str],
        tx_id: Optional[str] = None,
    ) -> IPFSUploadResult:
        evidence = {
            "version": "1.0",
            "type": "revocation",
            "consent_id": consent_id,
            "revoked_at": revoked_at.isoformat(),
            "revoked_by": revoked_by,
            "reason": reason,
            "tx_id": tx_id,
        }

        return await self.ipfs.upload_json(evidence)

    async def retrieve_evidence(self, cid: str) -> dict:
        return await self.ipfs.get_json(cid)

    @staticmethod
    def _compute_hash(
        consent_id: str,
        principal_wallet: str,
        fiduciary_wallet: str,
        purpose: str,
        granted_at: datetime,
    ) -> str:
        data = (
            f"{consent_id}:{principal_wallet}:{fiduciary_wallet}:{purpose}:{granted_at.isoformat()}"
        )
        return hashlib.sha256(data.encode()).hexdigest()


ipfs_client = IPFSClient()
evidence_store = ConsentEvidenceStore(ipfs_client)
