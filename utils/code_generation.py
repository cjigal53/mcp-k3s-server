"""Code generation utilities.

This module provides utilities for code generation functionality
that integrates with the webhook server.
"""

import asyncio
import logging
from typing import Any, Dict, Optional, Protocol
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class GenerationStatus(Enum):
    """Status of a code generation request."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class GenerationResult:
    """Result of a code generation request.

    Attributes:
        status: The status of the generation.
        prompt: The original prompt.
        code: The generated code (if successful).
        error: Error message (if failed).
        metadata: Additional metadata.
    """

    status: GenerationStatus
    prompt: str
    code: Optional[str] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class WebhookServerProtocol(Protocol):
    """Protocol defining the expected interface for a webhook server."""

    @property
    def is_running(self) -> bool:
        """Check if the server is running."""
        ...

    @property
    def code_generation_enabled(self) -> bool:
        """Check if code generation is enabled."""
        ...

    async def generate_code(self, prompt: str) -> Dict[str, Any]:
        """Generate code from a prompt."""
        ...


class CodeGenerationClient:
    """Client for interacting with the code generation service.

    This client manages code generation requests and handles
    server availability checking.
    """

    def __init__(
        self,
        server: WebhookServerProtocol,
        retry_count: int = 3,
        retry_delay: float = 1.0,
    ) -> None:
        """Initialize the code generation client.

        Args:
            server: The webhook server to use.
            retry_count: Number of retries on failure.
            retry_delay: Delay between retries in seconds.
        """
        self._server = server
        self._retry_count = retry_count
        self._retry_delay = retry_delay

    def is_available(self) -> bool:
        """Check if code generation is available.

        Returns:
            True if code generation is available, False otherwise.
        """
        return self._server.is_running and self._server.code_generation_enabled

    async def generate(self, prompt: str) -> GenerationResult:
        """Generate code from a prompt.

        Args:
            prompt: The code generation prompt.

        Returns:
            The generation result.
        """
        if not prompt or not prompt.strip():
            return GenerationResult(
                status=GenerationStatus.FAILED,
                prompt=prompt,
                error="Empty prompt provided",
            )

        if not self.is_available():
            return GenerationResult(
                status=GenerationStatus.FAILED,
                prompt=prompt,
                error="Code generation service is not available",
            )

        last_error: Optional[str] = None

        for attempt in range(self._retry_count):
            try:
                logger.debug(
                    "Attempting code generation (attempt %d/%d)",
                    attempt + 1,
                    self._retry_count,
                )

                result = await self._server.generate_code(prompt)

                return GenerationResult(
                    status=GenerationStatus.COMPLETED,
                    prompt=prompt,
                    code=result.get("generated_code"),
                    metadata=result.get("metrics"),
                )

            except Exception as e:
                last_error = str(e)
                logger.warning(
                    "Code generation attempt %d failed: %s",
                    attempt + 1,
                    last_error,
                )

                if attempt < self._retry_count - 1:
                    await asyncio.sleep(self._retry_delay)

        return GenerationResult(
            status=GenerationStatus.FAILED,
            prompt=prompt,
            error=f"Code generation failed after {self._retry_count} attempts: {last_error}",
        )

    async def generate_with_timeout(
        self,
        prompt: str,
        timeout: float = 30.0,
    ) -> GenerationResult:
        """Generate code with a timeout.

        Args:
            prompt: The code generation prompt.
            timeout: Maximum time to wait in seconds.

        Returns:
            The generation result.
        """
        try:
            return await asyncio.wait_for(
                self.generate(prompt),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            return GenerationResult(
                status=GenerationStatus.FAILED,
                prompt=prompt,
                error=f"Code generation timed out after {timeout} seconds",
            )


def validate_prompt(prompt: str) -> tuple[bool, Optional[str]]:
    """Validate a code generation prompt.

    Args:
        prompt: The prompt to validate.

    Returns:
        A tuple of (is_valid, error_message).
    """
    if not prompt:
        return False, "Prompt cannot be empty"

    if not prompt.strip():
        return False, "Prompt cannot be only whitespace"

    if len(prompt) > 10000:
        return False, "Prompt exceeds maximum length of 10000 characters"

    return True, None
