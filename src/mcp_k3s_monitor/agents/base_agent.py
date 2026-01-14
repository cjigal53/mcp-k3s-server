"""Base agent class with common functionality."""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import logging
from datetime import datetime
from pathlib import Path

from mcp_k3s_monitor.chatbot.mcp_client import MCPChatbotClient
from mcp_k3s_monitor.agents.config import AgentSystemConfig
from mcp_k3s_monitor.integrations.github_client import GitHubClient
from mcp_k3s_monitor.integrations.claude_client import ClaudeClient
from mcp_k3s_monitor.reports.generator import ReportGenerator
from mcp_k3s_monitor.workflows.executor import WorkflowExecutor

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """
    Abstract base class for all agents.

    Provides common functionality:
    - MCP cluster querying
    - Claude API interaction
    - GitHub API operations
    - Report generation
    - Workflow execution
    """

    def __init__(
        self,
        config: AgentSystemConfig,
        agent_type: str,
    ):
        self.config = config
        self.agent_type = agent_type
        self.logger = logging.getLogger(f"{__name__}.{agent_type}")

        # Initialize clients (lazy loading pattern)
        self._mcp_client: Optional[MCPChatbotClient] = None
        self._github_client: Optional[GitHubClient] = None
        self._claude_client: Optional[ClaudeClient] = None
        self._report_generator: Optional[ReportGenerator] = None
        self._workflow_executor: Optional[WorkflowExecutor] = None

    @property
    def mcp_client(self) -> MCPChatbotClient:
        """Lazy-load MCP client."""
        if self._mcp_client is None:
            self._mcp_client = MCPChatbotClient(
                server_command=self.config.mcp_server_command,
                timeout=self.config.mcp_timeout,
                auto_connect=True,
            )
            self.logger.info("Connected to MCP server")
        return self._mcp_client

    @property
    def github_client(self) -> GitHubClient:
        """Lazy-load GitHub client."""
        if self._github_client is None:
            self._github_client = GitHubClient(self.config)
        return self._github_client

    @property
    def claude_client(self) -> ClaudeClient:
        """Lazy-load Claude client."""
        if self._claude_client is None:
            self._claude_client = ClaudeClient(self.config)
        return self._claude_client

    @property
    def report_generator(self) -> ReportGenerator:
        """Lazy-load report generator."""
        if self._report_generator is None:
            self._report_generator = ReportGenerator(self.config)
        return self._report_generator

    @property
    def workflow_executor(self) -> WorkflowExecutor:
        """Lazy-load workflow executor."""
        if self._workflow_executor is None:
            self._workflow_executor = WorkflowExecutor(self.config)
        return self._workflow_executor

    @abstractmethod
    def get_agent_name(self) -> str:
        """Return human-readable agent name."""
        pass

    @abstractmethod
    def get_cluster_query_prompt(self, issue_data: Dict[str, Any]) -> str:
        """
        Build prompt for querying cluster based on issue.

        Args:
            issue_data: GitHub issue payload

        Returns:
            Prompt string for Claude
        """
        pass

    @abstractmethod
    def get_workflow_template(self) -> str:
        """Return path to workflow script template for this agent."""
        pass

    async def process_webhook(
        self,
        event_type: str,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Main entry point for processing webhook.

        Args:
            event_type: GitHub event type (issues, issue_comment, etc)
            payload: Webhook payload

        Returns:
            Processing result dictionary
        """
        try:
            self.logger.info(
                f"Processing {event_type} webhook for {self.agent_type} agent"
            )

            # Extract issue data
            issue = payload.get("issue", {})
            action = payload.get("action", "")

            # Only process opened/labeled issues
            if action not in ["opened", "labeled"]:
                return {"status": "skipped", "reason": f"Action {action} not handled"}

            # Check if issue has appropriate labels
            if not self._should_process_issue(issue):
                return {"status": "skipped", "reason": "Labels don't match agent"}

            # Run agent workflow
            result = await self._run_agent_workflow(issue, action)

            return {"status": "success", "result": result}

        except Exception as e:
            self.logger.error(f"Error processing webhook: {e}", exc_info=True)
            return {"status": "error", "error": str(e)}

    def _should_process_issue(self, issue: Dict[str, Any]) -> bool:
        """Check if issue labels match this agent."""
        issue_labels = {label["name"] for label in issue.get("labels", [])}
        agent_labels = set(self.config.agent_labels.get(self.agent_type, []))
        return bool(issue_labels & agent_labels)

    async def _run_agent_workflow(
        self,
        issue: Dict[str, Any],
        action: str,
    ) -> Dict[str, Any]:
        """
        Execute complete agent workflow.

        Steps:
        1. Query cluster status using MCP
        2. Send to Claude for analysis
        3. Generate HTML report
        4. Post GitHub comment
        5. Execute local workflow script
        """
        issue_number = issue["number"]
        issue_title = issue["title"]

        self.logger.info(f"Running workflow for issue #{issue_number}: {issue_title}")

        # Step 1: Query cluster
        cluster_data = await self._query_cluster(issue)

        # Step 2: Get Claude analysis
        analysis = await self._analyze_with_claude(issue, cluster_data)

        # Step 3: Generate HTML report
        report_path = await self._generate_report(issue, cluster_data, analysis)

        # Step 4: Post GitHub comment
        comment_url = await self._post_github_comment(issue_number, analysis, report_path)

        # Step 5: Execute workflow (in background)
        workflow_result = await self._execute_workflow(issue, cluster_data, analysis)

        return {
            "issue_number": issue_number,
            "cluster_data": cluster_data,
            "analysis": analysis,
            "report_path": str(report_path),
            "comment_url": comment_url,
            "workflow_result": workflow_result,
            "timestamp": datetime.utcnow().isoformat(),
        }

    async def _query_cluster(self, issue: Dict[str, Any]) -> Dict[str, Any]:
        """Query k3s cluster via MCP."""
        try:
            return {
                "health": self.mcp_client.get_cluster_health(),
                "pods": self.mcp_client.list_pods(),
                "deployments": self.mcp_client.list_deployments(),
                "nodes": self.mcp_client.list_nodes(),
                "namespaces": self.mcp_client.list_namespaces(),
            }
        except Exception as e:
            self.logger.error(f"Error querying cluster: {e}")
            return {"error": str(e)}

    async def _analyze_with_claude(
        self,
        issue: Dict[str, Any],
        cluster_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Send issue + cluster data to Claude for analysis."""
        prompt = self.get_cluster_query_prompt(issue)

        # Build comprehensive context
        context = f"""
Issue: {issue['title']}
{issue.get('body', '')}

Cluster Status:
{self._format_cluster_data(cluster_data)}
"""

        response = await self.claude_client.analyze(
            prompt=prompt,
            context=context,
            agent_type=self.agent_type,
        )

        return response

    def _format_cluster_data(self, cluster_data: Dict[str, Any]) -> str:
        """Format cluster data for Claude."""
        lines = []

        if "health" in cluster_data:
            health = cluster_data["health"]
            lines.append(f"Health: {health.get('status')}")
            lines.append(f"Nodes: {health.get('nodes_ready')}/{health.get('nodes_count')}")
            lines.append(f"Pods: {health.get('pods_running')} running")

        if "pods" in cluster_data and isinstance(cluster_data["pods"], list):
            lines.append(f"Total Pods: {len(cluster_data['pods'])}")

        return "\n".join(lines)

    async def _generate_report(
        self,
        issue: Dict[str, Any],
        cluster_data: Dict[str, Any],
        analysis: Dict[str, Any],
    ) -> Path:
        """Generate HTML dashboard."""
        return await self.report_generator.generate(
            agent_type=self.agent_type,
            issue=issue,
            cluster_data=cluster_data,
            analysis=analysis,
        )

    async def _post_github_comment(
        self,
        issue_number: int,
        analysis: Dict[str, Any],
        report_path: Path,
    ) -> str:
        """Post analysis as GitHub comment."""
        comment_body = self._format_github_comment(analysis, report_path)
        return await self.github_client.post_comment(issue_number, comment_body)

    @abstractmethod
    def _format_github_comment(
        self,
        analysis: Dict[str, Any],
        report_path: Path,
    ) -> str:
        """Format GitHub comment for this agent type."""
        pass

    async def _execute_workflow(
        self,
        issue: Dict[str, Any],
        cluster_data: Dict[str, Any],
        analysis: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute local workflow script."""
        template_path = self.get_workflow_template()

        return await self.workflow_executor.execute(
            template_path=template_path,
            variables={
                "issue": issue,
                "cluster_data": cluster_data,
                "analysis": analysis,
                "agent_type": self.agent_type,
            },
        )

    def cleanup(self):
        """Cleanup resources."""
        if self._mcp_client:
            self._mcp_client.disconnect()
