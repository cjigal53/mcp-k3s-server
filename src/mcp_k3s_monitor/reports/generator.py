"""HTML report/dashboard generator using Jinja2."""

from pathlib import Path
from datetime import datetime
from typing import Dict, Any
import logging
from jinja2 import Environment, FileSystemLoader, select_autoescape

from mcp_k3s_monitor.agents.config import AgentSystemConfig

logger = logging.getLogger(__name__)


class ReportGenerator:
    """HTML report/dashboard generator using Jinja2."""

    def __init__(self, config: AgentSystemConfig):
        self.config = config
        self.output_dir = config.reports_output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Setup Jinja2
        template_dir = config.report_template_dir or (
            Path(__file__).parent / "templates"
        )
        self.env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=select_autoescape(["html", "xml"]),
        )

        # Register custom filters
        self.env.filters["format_timestamp"] = self._format_timestamp
        self.env.filters["pod_status_icon"] = self._pod_status_icon

    async def generate(
        self,
        agent_type: str,
        issue: Dict[str, Any],
        cluster_data: Dict[str, Any],
        analysis: Dict[str, Any],
    ) -> Path:
        """
        Generate HTML dashboard report.

        Args:
            agent_type: Type of agent (feature/bug/chore)
            issue: GitHub issue data
            cluster_data: k3s cluster status
            analysis: Claude analysis results

        Returns:
            Path to generated HTML file
        """
        try:
            # Select template based on agent type
            template_name = f"{agent_type}_report.html"
            template = self.env.get_template(template_name)

            # Prepare template context
            context = {
                "agent_type": agent_type,
                "issue": issue,
                "cluster_data": cluster_data,
                "analysis": analysis,
                "generated_at": datetime.utcnow(),
                "report_title": f"{agent_type.title()} Report - Issue #{issue['number']}",
            }

            # Render HTML
            html_content = template.render(**context)

            # Save to file
            filename = f"{agent_type}_issue_{issue['number']}_{int(datetime.utcnow().timestamp())}.html"
            output_path = self.output_dir / filename

            output_path.write_text(html_content, encoding="utf-8")

            logger.info(f"Generated report: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Error generating report: {e}", exc_info=True)
            raise

    def _format_timestamp(self, dt):
        """Jinja2 filter for formatting timestamps."""
        if isinstance(dt, str):
            dt = datetime.fromisoformat(dt.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M:%S UTC")

    def _pod_status_icon(self, status: str) -> str:
        """Jinja2 filter for pod status icons."""
        icons = {
            "Running": "✅",
            "Pending": "⏳",
            "Failed": "❌",
            "Unknown": "❓",
        }
        return icons.get(status, "❓")
