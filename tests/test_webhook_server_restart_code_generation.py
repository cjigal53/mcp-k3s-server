"""Test: Verify code generation with restarted webhook server.

Issue #34: Testing that code generation is enabled and working after webhook server restart.

This module contains tests to verify that the code generation functionality
remains operational after the webhook server has been restarted.
"""

import asyncio
import pytest
from typing import Any, Dict, Optional
from unittest.mock import AsyncMock, MagicMock, patch


class WebhookServer:
    """Mock webhook server for testing purposes."""

    def __init__(self, host: str = "localhost", port: int = 8080) -> None:
        """Initialize the webhook server.

        Args:
            host: The host address to bind to.
            port: The port number to listen on.
        """
        self.host = host
        self.port = port
        self.is_running = False
        self.code_generation_enabled = True
        self._restart_count = 0

    async def start(self) -> None:
        """Start the webhook server."""
        self.is_running = True
        self.code_generation_enabled = True

    async def stop(self) -> None:
        """Stop the webhook server."""
        self.is_running = False

    async def restart(self) -> None:
        """Restart the webhook server."""
        await self.stop()
        await asyncio.sleep(0.1)  # Simulate restart delay
        await self.start()
        self._restart_count += 1

    @property
    def restart_count(self) -> int:
        """Get the number of times the server has been restarted."""
        return self._restart_count


class CodeGenerator:
    """Code generator that works with the webhook server."""

    def __init__(self, webhook_server: WebhookServer) -> None:
        """Initialize the code generator.

        Args:
            webhook_server: The webhook server instance to use.
        """
        self.webhook_server = webhook_server

    def is_enabled(self) -> bool:
        """Check if code generation is enabled.

        Returns:
            True if code generation is enabled, False otherwise.
        """
        return (
            self.webhook_server.is_running
            and self.webhook_server.code_generation_enabled
        )

    async def generate_code(self, prompt: str) -> Optional[Dict[str, Any]]:
        """Generate code based on the given prompt.

        Args:
            prompt: The prompt to generate code from.

        Returns:
            A dictionary containing the generated code and metadata,
            or None if generation failed.

        Raises:
            RuntimeError: If the webhook server is not running.
        """
        if not self.webhook_server.is_running:
            raise RuntimeError("Webhook server is not running")

        if not self.is_enabled():
            return None

        # Simulate code generation
        return {
            "status": "success",
            "prompt": prompt,
            "generated_code": f"# Generated code for: {prompt}\npass",
            "server_restart_count": self.webhook_server.restart_count,
        }


@pytest.fixture
def webhook_server() -> WebhookServer:
    """Create a webhook server fixture.

    Returns:
        A new WebhookServer instance.
    """
    return WebhookServer()


@pytest.fixture
def code_generator(webhook_server: WebhookServer) -> CodeGenerator:
    """Create a code generator fixture.

    Args:
        webhook_server: The webhook server to use.

    Returns:
        A new CodeGenerator instance.
    """
    return CodeGenerator(webhook_server)


class TestWebhookServerRestart:
    """Test suite for webhook server restart functionality."""

    @pytest.mark.asyncio
    async def test_server_starts_successfully(self, webhook_server: WebhookServer) -> None:
        """Test that the webhook server starts successfully."""
        assert not webhook_server.is_running
        await webhook_server.start()
        assert webhook_server.is_running

    @pytest.mark.asyncio
    async def test_server_stops_successfully(self, webhook_server: WebhookServer) -> None:
        """Test that the webhook server stops successfully."""
        await webhook_server.start()
        assert webhook_server.is_running
        await webhook_server.stop()
        assert not webhook_server.is_running

    @pytest.mark.asyncio
    async def test_server_restarts_successfully(self, webhook_server: WebhookServer) -> None:
        """Test that the webhook server restarts successfully."""
        await webhook_server.start()
        initial_restart_count = webhook_server.restart_count

        await webhook_server.restart()

        assert webhook_server.is_running
        assert webhook_server.restart_count == initial_restart_count + 1

    @pytest.mark.asyncio
    async def test_server_restart_count_increments(
        self, webhook_server: WebhookServer
    ) -> None:
        """Test that restart count increments correctly on multiple restarts."""
        await webhook_server.start()

        for i in range(3):
            await webhook_server.restart()
            assert webhook_server.restart_count == i + 1


class TestCodeGenerationAfterRestart:
    """Test suite for code generation after webhook server restart."""

    @pytest.mark.asyncio
    async def test_code_generation_enabled_after_start(
        self, webhook_server: WebhookServer, code_generator: CodeGenerator
    ) -> None:
        """Test that code generation is enabled after server start."""
        await webhook_server.start()
        assert code_generator.is_enabled()

    @pytest.mark.asyncio
    async def test_code_generation_disabled_when_server_stopped(
        self, webhook_server: WebhookServer, code_generator: CodeGenerator
    ) -> None:
        """Test that code generation is disabled when server is stopped."""
        await webhook_server.start()
        await webhook_server.stop()
        assert not code_generator.is_enabled()

    @pytest.mark.asyncio
    async def test_code_generation_enabled_after_restart(
        self, webhook_server: WebhookServer, code_generator: CodeGenerator
    ) -> None:
        """Test that code generation is enabled after server restart."""
        await webhook_server.start()
        await webhook_server.restart()
        assert code_generator.is_enabled()

    @pytest.mark.asyncio
    async def test_code_generation_works_after_restart(
        self, webhook_server: WebhookServer, code_generator: CodeGenerator
    ) -> None:
        """Test that code generation works correctly after server restart."""
        await webhook_server.start()
        await webhook_server.restart()

        result = await code_generator.generate_code("Create a hello world function")

        assert result is not None
        assert result["status"] == "success"
        assert "generated_code" in result
        assert result["server_restart_count"] == 1

    @pytest.mark.asyncio
    async def test_code_generation_works_after_multiple_restarts(
        self, webhook_server: WebhookServer, code_generator: CodeGenerator
    ) -> None:
        """Test that code generation works after multiple server restarts."""
        await webhook_server.start()

        for i in range(5):
            await webhook_server.restart()
            result = await code_generator.generate_code(f"Test prompt {i}")

            assert result is not None
            assert result["status"] == "success"
            assert result["server_restart_count"] == i + 1

    @pytest.mark.asyncio
    async def test_code_generation_fails_when_server_not_running(
        self, webhook_server: WebhookServer, code_generator: CodeGenerator
    ) -> None:
        """Test that code generation fails when server is not running."""
        with pytest.raises(RuntimeError, match="Webhook server is not running"):
            await code_generator.generate_code("Test prompt")

    @pytest.mark.asyncio
    async def test_code_generation_preserves_prompt_after_restart(
        self, webhook_server: WebhookServer, code_generator: CodeGenerator
    ) -> None:
        """Test that generated code preserves the prompt after restart."""
        await webhook_server.start()
        await webhook_server.restart()

        prompt = "Create a fibonacci function"
        result = await code_generator.generate_code(prompt)

        assert result is not None
        assert result["prompt"] == prompt
        assert prompt in result["generated_code"]


class TestCodeGenerationIntegration:
    """Integration tests for code generation with webhook server."""

    @pytest.mark.asyncio
    async def test_full_lifecycle_with_code_generation(
        self, webhook_server: WebhookServer, code_generator: CodeGenerator
    ) -> None:
        """Test the full lifecycle: start, generate, restart, generate, stop."""
        # Start server
        await webhook_server.start()
        assert code_generator.is_enabled()

        # Generate code before restart
        result_before = await code_generator.generate_code("Before restart")
        assert result_before is not None
        assert result_before["status"] == "success"

        # Restart server
        await webhook_server.restart()
        assert code_generator.is_enabled()

        # Generate code after restart
        result_after = await code_generator.generate_code("After restart")
        assert result_after is not None
        assert result_after["status"] == "success"
        assert result_after["server_restart_count"] == 1

        # Stop server
        await webhook_server.stop()
        assert not code_generator.is_enabled()

    @pytest.mark.asyncio
    async def test_concurrent_code_generation_after_restart(
        self, webhook_server: WebhookServer, code_generator: CodeGenerator
    ) -> None:
        """Test concurrent code generation requests after restart."""
        await webhook_server.start()
        await webhook_server.restart()

        prompts = [f"Concurrent prompt {i}" for i in range(10)]
        tasks = [code_generator.generate_code(prompt) for prompt in prompts]

        results = await asyncio.gather(*tasks)

        assert all(result is not None for result in results)
        assert all(result["status"] == "success" for result in results)

    @pytest.mark.asyncio
    async def test_code_generation_state_consistency_after_restart(
        self, webhook_server: WebhookServer, code_generator: CodeGenerator
    ) -> None:
        """Test that code generation state is consistent after restart."""
        await webhook_server.start()

        # Check initial state
        assert webhook_server.code_generation_enabled is True
        assert code_generator.is_enabled() is True

        # Restart and verify state
        await webhook_server.restart()

        assert webhook_server.code_generation_enabled is True
        assert code_generator.is_enabled() is True
        assert webhook_server.is_running is True
