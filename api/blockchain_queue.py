"""Async blockchain processing queue using Redis.

This module decouples blockchain operations from API responses,
allowing immediate response times while blockchain transactions
process in the background.
"""

import json
import logging
import asyncio
from typing import Optional, Callable, Dict, Any
from datetime import datetime, timezone
from uuid import uuid4

import redis.asyncio as redis

logger = logging.getLogger(__name__)


class BlockchainQueue:
    """
    Async queue for blockchain operations.
    
    Instead of blocking API responses for 3-5 seconds, blockchain operations
    are queued and processed in the background. Status is tracked in database.
    """
    
    QUEUE_NAME = "blockchain:operations"
    PROCESSING_KEY = "blockchain:processing"
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self._running = False
    
    async def enqueue_operation(
        self,
        operation_type: str,  # 'register_consent', 'revoke_consent', etc.
        params: Dict[str, Any],
        consent_id: Optional[str] = None,
        priority: int = 0,
    ) -> str:
        """
        Queue a blockchain operation for background processing.
        
        Returns:
            operation_id for tracking status
        """
        operation_id = str(uuid4())
        
        message = {
            "operation_id": operation_id,
            "type": operation_type,
            "params": json.dumps(params),
            "consent_id": consent_id,
            "priority": priority,
            "queued_at": datetime.now(timezone.utc).isoformat(),
            "status": "queued",
        }
        
        # Add to Redis stream
        await self.redis.xadd(
            self.QUEUE_NAME,
            message,
            maxlen=10000,  # Keep last 10k operations
        )
        
        logger.info(f"Queued blockchain operation: {operation_id} ({operation_type})")
        return operation_id
    
    async def start_processor(self, process_fn: Callable):
        """
        Start background processor that dequeues and executes operations.
        
        Args:
            process_fn: Async function that takes operation dict and executes it
        """
        self._running = True
        logger.info("Starting blockchain queue processor")
        
        while self._running:
            try:
                # Read next operation from stream
                response = await self.redis.xread(
                    {self.QUEUE_NAME: "0"},
                    count=1,
                    block=1000,  # Block for 1 second
                )
                
                if not response:
                    continue
                
                stream_name, messages = response[0]
                
                for message_id, message in messages:
                    # Acquire distributed lock
                    acquired = await self.redis.set(
                        self.PROCESSING_KEY,
                        message_id,
                        nx=True,
                        ex=60,  # 60 second timeout
                    )
                    
                    if not acquired:
                        continue  # Another instance is processing
                    
                    try:
                        await process_fn(message)
                        
                        # Mark as completed
                        message["status"] = "completed"
                        message["completed_at"] = datetime.now(timezone.utc).isoformat()
                        
                        # Remove from stream
                        await self.redis.xdel(self.QUEUE_NAME, message_id)
                        
                        logger.info(f"Completed blockchain operation: {message['operation_id']}")
                        
                    except Exception as e:
                        logger.error(f"Failed blockchain operation: {message['operation_id']}: {e}")
                        
                        # Mark as failed
                        message["status"] = "failed"
                        message["error"] = str(e)
                        message["failed_at"] = datetime.now(timezone.utc).isoformat()
                        
                        # Move to dead letter queue
                        await self.redis.xadd(
                            f"{self.QUEUE_NAME}:dead_letter",
                            message,
                            maxlen=1000,
                        )
                        
                        # Remove from main stream
                        await self.redis.xdel(self.QUEUE_NAME, message_id)
                    
                    finally:
                        # Release lock
                        await self.redis.delete(self.PROCESSING_KEY)
            
            except Exception as e:
                logger.error(f"Error in blockchain queue processor: {e}")
                await asyncio.sleep(1)
    
    async def stop_processor(self):
        """Stop the background processor."""
        self._running = False
        logger.info("Stopping blockchain queue processor")
    
    async def get_queue_length(self) -> int:
        """Get number of pending operations."""
        return await self.redis.xlen(self.QUEUE_NAME)
    
    async def get_operation_status(self, operation_id: str) -> Optional[Dict[str, Any]]:
        """
        Get status of a specific operation.
        Note: This requires reading from stream - may need to scan recent messages.
        """
        # Read recent operations
        messages = await self.redis.xrevrange(
            self.QUEUE_NAME,
            count=100,
        )
        
        for message_id, message in messages:
            if message.get("operation_id") == operation_id:
                return {
                    "operation_id": operation_id,
                    "status": message.get("status", "unknown"),
                    "type": message.get("type"),
                    "queued_at": message.get("queued_at"),
                    "completed_at": message.get("completed_at"),
                    "error": message.get("error"),
                }
        
        return None
