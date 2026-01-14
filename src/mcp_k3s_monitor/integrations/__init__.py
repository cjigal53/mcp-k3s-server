"""Integrations with external services."""

from mcp_k3s_monitor.integrations.claude_client import ClaudeClient
from mcp_k3s_monitor.integrations.github_client import GitHubClient

__all__ = ["ClaudeClient", "GitHubClient"]
