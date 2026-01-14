"""GitHub REST API client wrapper."""

import requests
from typing import Dict, Any, List
import logging

from mcp_k3s_monitor.agents.config import AgentSystemConfig

logger = logging.getLogger(__name__)


class GitHubClient:
    """Wrapper for GitHub REST API."""

    def __init__(self, config: AgentSystemConfig):
        self.config = config
        self.token = config.github_token.get_secret_value()
        self.repo_owner = config.github_repo_owner
        self.repo_name = config.github_repo_name
        self.base_url = "https://api.github.com"

        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github.v3+json",
        })

    async def post_comment(
        self,
        issue_number: int,
        body: str,
    ) -> str:
        """
        Post comment on GitHub issue.

        Args:
            issue_number: Issue number
            body: Comment body (supports Markdown)

        Returns:
            Comment URL
        """
        try:
            url = (
                f"{self.base_url}/repos/{self.repo_owner}/"
                f"{self.repo_name}/issues/{issue_number}/comments"
            )

            response = self.session.post(
                url,
                json={"body": body},
            )
            response.raise_for_status()

            comment_data = response.json()
            comment_url = comment_data["html_url"]

            logger.info(f"Posted comment on issue #{issue_number}: {comment_url}")
            return comment_url

        except Exception as e:
            logger.error(f"Error posting GitHub comment: {e}", exc_info=True)
            raise

    async def add_labels(
        self,
        issue_number: int,
        labels: List[str],
    ):
        """Add labels to issue."""
        try:
            url = (
                f"{self.base_url}/repos/{self.repo_owner}/"
                f"{self.repo_name}/issues/{issue_number}/labels"
            )

            response = self.session.post(
                url,
                json={"labels": labels},
            )
            response.raise_for_status()

            logger.info(f"Added labels to issue #{issue_number}: {labels}")

        except Exception as e:
            logger.error(f"Error adding labels: {e}", exc_info=True)
            raise

    async def update_issue(
        self,
        issue_number: int,
        state: str = None,
        assignees: List[str] = None,
    ):
        """Update issue state or assignees."""
        try:
            url = (
                f"{self.base_url}/repos/{self.repo_owner}/"
                f"{self.repo_name}/issues/{issue_number}"
            )

            data = {}
            if state:
                data["state"] = state
            if assignees is not None:
                data["assignees"] = assignees

            response = self.session.patch(url, json=data)
            response.raise_for_status()

            logger.info(f"Updated issue #{issue_number}")

        except Exception as e:
            logger.error(f"Error updating issue: {e}", exc_info=True)
            raise
