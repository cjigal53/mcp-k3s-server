"""Anthropic Claude API client wrapper."""

import anthropic
from typing import Dict, Any
import logging
import json

from mcp_k3s_monitor.agents.config import AgentSystemConfig

logger = logging.getLogger(__name__)


class ClaudeClient:
    """Wrapper for Anthropic Claude API."""

    def __init__(self, config: AgentSystemConfig):
        self.config = config
        self.client = anthropic.Anthropic(
            api_key=config.anthropic_api_key.get_secret_value()
        )
        self.model = config.anthropic_model

    async def analyze(
        self,
        prompt: str,
        context: str,
        agent_type: str,
    ) -> Dict[str, Any]:
        """
        Send analysis request to Claude.

        Args:
            prompt: System prompt describing analysis task
            context: User context (issue + cluster data)
            agent_type: Type of agent making the request

        Returns:
            Structured analysis response
        """
        try:
            # Use structured output format
            system_message = f"""{prompt}

Return your analysis as a JSON object with the following structure:
{{
    "summary": "Brief executive summary",
    "severity": "Critical/High/Medium/Low (for bugs) or N/A",
    "root_cause": "Root cause analysis (for bugs) or N/A",
    "recommendations": ["list", "of", "actionable", "recommendations"],
    "debugging_steps": ["step-by-step", "debugging", "guide"] (for bugs),
    "implementation_steps": ["step-by-step", "implementation", "guide"] (for features),
    "risks": ["potential", "risks", "or", "concerns"],
    "impact": "High/Medium/Low - expected impact of changes"
}}
"""

            message = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=system_message,
                messages=[
                    {
                        "role": "user",
                        "content": context,
                    }
                ],
            )

            # Parse response
            response_text = message.content[0].text

            # Try to parse as JSON
            try:
                analysis = json.loads(response_text)
            except json.JSONDecodeError:
                # Fallback to plain text
                analysis = {
                    "summary": response_text,
                    "recommendations": [],
                    "raw_response": response_text,
                }

            logger.info(f"Claude analysis complete for {agent_type} agent")
            return analysis

        except Exception as e:
            logger.error(f"Error calling Claude API: {e}", exc_info=True)
            return {
                "error": str(e),
                "summary": "Analysis failed due to API error",
                "recommendations": [],
            }
