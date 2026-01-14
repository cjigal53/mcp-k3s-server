"""Configuration for webhook-based agent system."""

from pydantic_settings import BaseSettings
from pydantic import Field, SecretStr
from typing import Dict, List
from pathlib import Path


class AgentSystemConfig(BaseSettings):
    """Configuration for webhook-based agent system."""

    # GitHub Configuration
    github_token: SecretStr = Field(..., description="GitHub API token")
    github_webhook_secret: SecretStr = Field(..., description="Webhook signature secret")
    github_repo_owner: str = Field(..., description="Repository owner")
    github_repo_name: str = Field(..., description="Repository name")

    # Anthropic Configuration
    anthropic_api_key: SecretStr = Field(..., description="Anthropic API key")
    anthropic_model: str = Field(
        default="claude-3-5-sonnet-20241022", description="Claude model"
    )

    # MCP Server Configuration
    mcp_server_command: str = Field(
        default="python -m mcp_k3s_monitor",
        description="Command to start MCP server",
    )
    mcp_timeout: int = Field(default=30, description="MCP operation timeout")

    # FastAPI Server Configuration
    webhook_host: str = Field(default="0.0.0.0", description="Webhook server host")
    webhook_port: int = Field(default=8000, description="Webhook server port")
    webhook_path_prefix: str = Field(
        default="/webhooks", description="Webhook path prefix"
    )

    # Agent Configuration
    agent_labels: Dict[str, List[str]] = Field(
        default={
            "feature": ["feature", "enhancement", "feature-request"],
            "bug": ["bug", "error", "issue"],
            "chore": ["chore", "maintenance", "refactor", "docs"],
        },
        description="Label mappings for agent routing",
    )

    # Report Configuration
    reports_output_dir: Path = Field(
        default=Path("./reports"), description="Directory for generated reports"
    )
    report_template_dir: Path | None = Field(
        default=None, description="Custom template directory (uses default if None)"
    )

    # Workflow Configuration
    workflows_dir: Path = Field(
        default=Path("./workflows"), description="Directory containing workflow scripts"
    )
    workflow_timeout: int = Field(
        default=300, description="Workflow execution timeout"
    )

    # Logging Configuration
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log format",
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        env_prefix = "AGENT_"  # All env vars prefixed with AGENT_


def get_config() -> AgentSystemConfig:
    """Load and return agent configuration."""
    return AgentSystemConfig()
