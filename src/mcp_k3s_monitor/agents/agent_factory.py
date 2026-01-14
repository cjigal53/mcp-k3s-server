"""Agent factory for creating agent instances."""

from mcp_k3s_monitor.agents.config import AgentSystemConfig
from mcp_k3s_monitor.agents.feature_agent import FeatureAgent
from mcp_k3s_monitor.agents.bug_agent import BugAgent
from mcp_k3s_monitor.agents.chore_agent import ChoreAgent


class AgentFactory:
    """Factory for creating agent instances."""

    def __init__(self, config: AgentSystemConfig):
        self.config = config

    def create_agent(self, agent_type: str):
        """Create an agent of the specified type."""
        if agent_type == "feature":
            return FeatureAgent(self.config)
        elif agent_type == "bug":
            return BugAgent(self.config)
        elif agent_type == "chore":
            return ChoreAgent(self.config)
        else:
            raise ValueError(f"Unknown agent type: {agent_type}")
