"""Webhook server implementation for code generation.

This module provides the core webhook server functionality that handles
code generation requests and manages server lifecycle.
"""

import asyncio
import logging
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class ServerState(Enum):
    """Enumeration of possible server states."""

    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    RESTARTING = "restarting"


@dataclass
class ServerConfig:
    """Configuration for the webhook server.

    Attributes:
        host: The host address to bind to.
        port: The port number to listen on.
        enable_code_generation: Whether code generation is enabled.
        max_connections: Maximum number of concurrent connections.
        restart_delay: Delay in seconds between stop and start during restart.
    """

    host: str = "0.0.0.0"
    port: int = 8080
    enable_code_generation: bool = True
    max_connections: int = 100
    restart_delay: float = 0.5


@dataclass
class ServerMetrics:
    """Metrics tracking for the webhook server.

    Attributes:
        restart_count: Number of times the server has been restarted.
        requests_handled: Total number of requests handled.
        code_generations: Total number of code generation requests.
        errors: Total number of errors encountered.
    """

    restart_count: int = 0
    requests_handled: int = 0
    code_generations: int = 0
    errors: int = 0


class WebhookServer:
    """Webhook server for handling code generation requests.

    This server handles incoming webhook requests and manages code generation
    functionality. It supports graceful restart while maintaining state.

    Attributes:
        config: Server configuration.
        state: Current server state.
        metrics: Server metrics.
    """

    def __init__(self, config: Optional[ServerConfig] = None) -> None:
        """Initialize the webhook server.

        Args:
            config: Server configuration. If None, uses defaults.
        """
        self.config = config or ServerConfig()
        self._state = ServerState.STOPPED
        self._metrics = ServerMetrics()
        self._handlers: List[Callable] = []
        self._lock = asyncio.Lock()
        self._code_generation_enabled = self.config.enable_code_generation

    @property
    def state(self) -> ServerState:
        """Get the current server state."""
        return self._state

    @property
    def metrics(self) -> ServerMetrics:
        """Get the server metrics."""
        return self._metrics

    @property
    def is_running(self) -> bool:
        """Check if the server is currently running."""
        return self._state == ServerState.RUNNING

    @property
    def code_generation_enabled(self) -> bool:
        """Check if code generation is enabled."""
        return self._code_generation_enabled and self.is_running

    async def start(self) -> None:
        """Start the webhook server.

        Raises:
            RuntimeError: If the server is already running.
        """
        async with self._lock:
            if self._state == ServerState.RUNNING:
                raise RuntimeError("Server is already running")

            logger.info("Starting webhook server on %s:%d", self.config.host, self.config.port)
            self._state = ServerState.STARTING

            try:
                # Initialize server components
                await self._initialize()
                self._state = ServerState.RUNNING
                self._code_generation_enabled = self.config.enable_code_generation
                logger.info("Webhook server started successfully")
            except Exception as e:
                self._state = ServerState.STOPPED
                self._metrics.errors += 1
                logger.error("Failed to start webhook server: %s", e)
                raise

    async def stop(self) -> None:
        """Stop the webhook server.

        Raises:
            RuntimeError: If the server is not running.
        """
        async with self._lock:
            if self._state == ServerState.STOPPED:
                logger.warning("Server is already stopped")
                return

            logger.info("Stopping webhook server")
            self._state = ServerState.STOPPING

            try:
                await self._cleanup()
                self._state = ServerState.STOPPED
                logger.info("Webhook server stopped successfully")
            except Exception as e:
                self._metrics.errors += 1
                logger.error("Error stopping webhook server: %s", e)
                raise

    async def restart(self) -> None:
        """Restart the webhook server.

        This performs a graceful restart, ensuring code generation
        is re-enabled after the restart.
        """
        logger.info("Restarting webhook server")
        self._state = ServerState.RESTARTING

        try:
            # Stop if running
            if self.is_running or self._state != ServerState.STOPPED:
                await self.stop()

            # Wait before restarting
            await asyncio.sleep(self.config.restart_delay)

            # Start again
            await self.start()

            self._metrics.restart_count += 1
            logger.info(
                "Webhook server restarted successfully (restart count: %d)",
                self._metrics.restart_count
            )
        except Exception as e:
            self._metrics.errors += 1
            logger.error("Failed to restart webhook server: %s", e)
            raise

    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle an incoming webhook request.

        Args:
            request: The incoming request data.

        Returns:
            The response data.

        Raises:
            RuntimeError: If the server is not running.
        """
        if not self.is_running:
            raise RuntimeError("Server is not running")

        self._metrics.requests_handled += 1

        return {
            "status": "success",
            "server_state": self._state.value,
            "restart_count": self._metrics.restart_count,
        }

    async def generate_code(self, prompt: str) -> Dict[str, Any]:
        """Generate code based on the given prompt.

        Args:
            prompt: The code generation prompt.

        Returns:
            The generated code response.

        Raises:
            RuntimeError: If code generation is not available.
        """
        if not self.is_running:
            raise RuntimeError("Server is not running")

        if not self.code_generation_enabled:
            raise RuntimeError("Code generation is not enabled")

        self._metrics.code_generations += 1

        logger.debug("Generating code for prompt: %s", prompt[:50])

        return {
            "status": "success",
            "prompt": prompt,
            "generated_code": f"# Generated code\n# Prompt: {prompt}\npass",
            "metrics": {
                "restart_count": self._metrics.restart_count,
                "total_generations": self._metrics.code_generations,
            },
        }

    async def _initialize(self) -> None:
        """Initialize server components."""
        # Simulate initialization
        await asyncio.sleep(0.01)

    async def _cleanup(self) -> None:
        """Clean up server resources."""
        # Simulate cleanup
        await asyncio.sleep(0.01)

    def register_handler(self, handler: Callable) -> None:
        """Register a request handler.

        Args:
            handler: The handler function to register.
        """
        self._handlers.append(handler)

    def get_status(self) -> Dict[str, Any]:
        """Get the current server status.

        Returns:
            A dictionary containing server status information.
        """
        return {
            "state": self._state.value,
            "is_running": self.is_running,
            "code_generation_enabled": self.code_generation_enabled,
            "config": {
                "host": self.config.host,
                "port": self.config.port,
            },
            "metrics": {
                "restart_count": self._metrics.restart_count,
                "requests_handled": self._metrics.requests_handled,
                "code_generations": self._metrics.code_generations,
                "errors": self._metrics.errors,
            },
        }
