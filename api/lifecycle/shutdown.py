"""Graceful Shutdown Handler for ConsentChain."""

from typing import List, Callable, Awaitable, Optional, Set
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timezone
import asyncio
import signal
import logging

logger = logging.getLogger(__name__)


class ShutdownPhase(str, Enum):
    RUNNING = "running"
    SHUTDOWN_REQUESTED = "shutdown_requested"
    DRAINING = "draining"
    CLEANUP = "cleanup"
    COMPLETE = "complete"


@dataclass
class ShutdownStats:
    phase: ShutdownPhase = ShutdownPhase.RUNNING
    shutdown_requested_at: Optional[datetime] = None
    active_requests: int = 0
    completed_requests: int = 0
    cleanup_handlers_run: int = 0
    errors: List[str] = field(default_factory=list)


class GracefulShutdown:
    DEFAULT_TIMEOUT = 30.0
    DRAIN_TIMEOUT = 10.0

    def __init__(self, timeout: float = DEFAULT_TIMEOUT):
        self.timeout = timeout
        self._stats = ShutdownStats()
        self._handlers: List[tuple[str, Callable[[], Awaitable[None]]]] = []
        self._active_requests: Set[int] = set()
        self._request_counter = 0
        self._lock = asyncio.Lock()
        self._shutdown_event = asyncio.Event()
        self._drain_complete = asyncio.Event()

    @property
    def is_shutting_down(self) -> bool:
        return self._stats.phase != ShutdownPhase.RUNNING

    @property
    def phase(self) -> ShutdownPhase:
        return self._stats.phase

    def register_handler(self, name: str, handler: Callable[[], Awaitable[None]]):
        self._handlers.append((name, handler))
        logger.debug(f"Registered shutdown handler: {name}")

    class RequestContext:
        def __init__(self, shutdown: "GracefulShutdown"):
            self._shutdown = shutdown
            self._request_id: Optional[int] = None

        async def __aenter__(self):
            if self._shutdown.is_shutting_down:
                raise RuntimeError("Server is shutting down")

            async with self._shutdown._lock:
                self._shutdown._request_counter += 1
                self._request_id = self._shutdown._request_counter
                self._shutdown._active_requests.add(self._request_id)

            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            if self._request_id is not None:
                async with self._shutdown._lock:
                    self._shutdown._active_requests.discard(self._request_id)
                    self._shutdown._stats.completed_requests += 1

                if self._shutdown.is_shutting_down and not self._shutdown._active_requests:
                    self._shutdown._drain_complete.set()

            return False

    def request_context(self):
        return self.RequestContext(self)

    def install_signal_handlers(self):
        loop = asyncio.get_event_loop()

        for sig in (signal.SIGTERM, signal.SIGINT):
            try:
                loop.add_signal_handler(
                    sig,
                    lambda s=sig: asyncio.create_task(self.initiate_shutdown(s.name)),
                )
                logger.debug(f"Installed signal handler for {sig.name}")
            except NotImplementedError:
                logger.warning(f"Could not install signal handler for {sig.name}")

    async def initiate_shutdown(self, reason: str = "signal"):
        if self._stats.phase != ShutdownPhase.RUNNING:
            logger.warning(f"Shutdown already in progress: {self._stats.phase}")
            return

        self._stats.phase = ShutdownPhase.SHUTDOWN_REQUESTED
        self._stats.shutdown_requested_at = datetime.now(timezone.utc)

        logger.info(
            f"Shutdown initiated: reason={reason}, active_requests={len(self._active_requests)}"
        )

        self._shutdown_event.set()

        await self._drain_requests()
        await self._run_cleanup_handlers()

        self._stats.phase = ShutdownPhase.COMPLETE
        logger.info("Graceful shutdown complete")

    async def _drain_requests(self):
        self._stats.phase = ShutdownPhase.DRAINING

        if not self._active_requests:
            logger.info("No active requests to drain")
            return

        logger.info(
            f"Draining {len(self._active_requests)} active requests "
            f"(timeout: {self.DRAIN_TIMEOUT}s)"
        )

        try:
            await asyncio.wait_for(
                self._drain_complete.wait(),
                timeout=self.DRAIN_TIMEOUT,
            )
            logger.info("All requests drained successfully")
        except asyncio.TimeoutError:
            logger.warning(
                f"Drain timeout exceeded, {len(self._active_requests)} requests still pending"
            )

    async def _run_cleanup_handlers(self):
        self._stats.phase = ShutdownPhase.CLEANUP

        logger.info(f"Running {len(self._handlers)} cleanup handlers")

        for name, handler in self._handlers:
            try:
                logger.debug(f"Running cleanup handler: {name}")
                await asyncio.wait_for(handler(), timeout=5.0)
                self._stats.cleanup_handlers_run += 1
                logger.debug(f"Cleanup handler complete: {name}")
            except asyncio.TimeoutError:
                error = f"Cleanup handler timeout: {name}"
                logger.error(error)
                self._stats.errors.append(error)
            except Exception as e:
                error = f"Cleanup handler error: {name} - {e}"
                logger.error(error)
                self._stats.errors.append(error)

    def get_stats(self) -> dict:
        return {
            "phase": self._stats.phase.value,
            "shutdown_requested_at": self._stats.shutdown_requested_at.isoformat()
            if self._stats.shutdown_requested_at
            else None,
            "active_requests": len(self._active_requests),
            "completed_requests": self._stats.completed_requests,
            "cleanup_handlers_run": self._stats.cleanup_handlers_run,
            "registered_handlers": len(self._handlers),
            "errors": self._stats.errors,
        }

    async def wait_for_shutdown(self):
        await self._shutdown_event.wait()


_shutdown_handler: Optional[GracefulShutdown] = None


def get_shutdown_handler() -> GracefulShutdown:
    global _shutdown_handler
    if _shutdown_handler is None:
        _shutdown_handler = GracefulShutdown()
    return _shutdown_handler


async def setup_graceful_shutdown(
    app, timeout: float = GracefulShutdown.DEFAULT_TIMEOUT
) -> GracefulShutdown:
    shutdown = GracefulShutdown(timeout=timeout)
    shutdown.install_signal_handlers()

    global _shutdown_handler
    _shutdown_handler = shutdown

    logger.info("Graceful shutdown configured")
    return shutdown
