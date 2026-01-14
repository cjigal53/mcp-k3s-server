#!/usr/bin/env python3
"""
Interactive K3s Chatbot Example

Demonstrates how to use MCPChatbotClient to create an interactive chatbot
that queries a k3s cluster using natural language.

Usage:
    python examples/claude_chatbot_integration.py
"""

import sys
import re
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mcp_k3s_monitor.chatbot import MCPChatbotClient


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class K3sChatbot:
    """Interactive chatbot for k3s cluster queries."""

    def __init__(self, server_command: str = "python -m mcp_k3s_monitor"):
        """Initialize chatbot with MCP client."""
        self.client = MCPChatbotClient(server_command=server_command)
        self.available_tools = []
        self._load_tools()

    def _load_tools(self) -> None:
        """Load available tools from server."""
        try:
            self.available_tools = self.client.list_tools()
            tool_names = [t.get("name", "unknown") for t in self.available_tools]
            logger.info(f"Loaded {len(tool_names)} tools: {', '.join(tool_names)}")
        except Exception as e:
            logger.warning(f"Could not load tools: {e}")
            self.available_tools = []

    def handle_query(self, user_query: str) -> str:
        """
        Handle a user query and return response.

        Args:
            user_query: User's natural language query.

        Returns:
            Response string.
        """
        query_lower = user_query.lower()

        # Cluster health queries
        if any(word in query_lower for word in ["estado", "health", "salud", "estado del cluster", "cómo está"]):
            return self._handle_cluster_health()

        # Pod queries
        elif any(word in query_lower for word in ["pods", "contenedores", "containers", "pod"]):
            namespace = self._extract_namespace(user_query)
            return self._handle_list_pods(namespace)

        # Log queries
        elif any(word in query_lower for word in ["logs", "log", "error", "output"]):
            pod_name = self._extract_pod_name(user_query)
            namespace = self._extract_namespace(user_query) or "default"
            if pod_name:
                return self._handle_pod_logs(pod_name, namespace)
            else:
                return "I need a pod name to fetch logs. Please specify which pod."

        # Deployment queries
        elif any(word in query_lower for word in ["deployment", "deployments", "deploy"]):
            namespace = self._extract_namespace(user_query)
            return self._handle_list_deployments(namespace)

        # Node queries
        elif any(word in query_lower for word in ["nodes", "node", "worker", "master"]):
            return self._handle_list_nodes()

        # Namespace queries
        elif any(word in query_lower for word in ["namespace", "namespaces", "namespaces"]):
            return self._handle_list_namespaces()

        # Help
        elif any(word in query_lower for word in ["help", "ayuda", "what can you", "qué puedes"]):
            return self._get_help_text()

        else:
            return (
                "I didn't understand that query. Available commands:\n"
                "- Cluster health/status\n"
                "- List pods [in <namespace>]\n"
                "- Get logs for <pod_name> [in <namespace>]\n"
                "- List deployments [in <namespace>]\n"
                "- List nodes\n"
                "- List namespaces\n\n"
                "Type 'help' for more information."
            )

    def _handle_cluster_health(self) -> str:
        """Get cluster health information."""
        try:
            health = self.client.get_cluster_health()

            return f"""
🏥 Cluster Health Status:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Status: {health.get('status', 'Unknown')}
Nodes: {health.get('nodes_ready', 0)}/{health.get('nodes_count', 0)} ready
Pods: {health.get('pods_running', 0)} running, {health.get('pods_pending', 0)} pending, {health.get('pods_failed', 0)} failed
Services: {health.get('services_count', 0)}
Deployments: {health.get('deployments_count', 0)}
""".strip()
        except Exception as e:
            return f"❌ Error getting cluster health: {e}"

    def _handle_list_pods(self, namespace: str = None) -> str:
        """List pods in namespace."""
        try:
            pods = self.client.list_pods(namespace=namespace)

            if not pods:
                return f"No pods found{f' in {namespace}' if namespace else ''}."

            response = f"📦 Pods{f' in {namespace}' if namespace else ''}:\n" + "━" * 60 + "\n"

            for pod in pods[:20]:  # Limit to 20 pods
                status_emoji = "✅" if pod.get("status") == "Running" else "⏳"
                response += (
                    f"{status_emoji} {pod.get('name', 'unknown'):40} "
                    f"{pod.get('status', 'Unknown'):10} "
                    f"{pod.get('ready', '?/?'):6}\n"
                )

            if len(pods) > 20:
                response += f"\n... and {len(pods) - 20} more pods"

            return response
        except Exception as e:
            return f"❌ Error listing pods: {e}"

    def _handle_pod_logs(self, pod_name: str, namespace: str) -> str:
        """Get pod logs."""
        try:
            logs = self.client.get_pod_logs(
                pod_name=pod_name,
                namespace=namespace,
                lines=30,
            )

            # Limit output
            lines = logs.split("\n")
            if len(lines) > 30:
                lines = lines[-30:]

            response = f"📄 Logs for {pod_name} ({namespace}):\n" + "━" * 60 + "\n"
            response += "\n".join(lines)

            return response
        except Exception as e:
            return f"❌ Error getting pod logs: {e}"

    def _handle_list_deployments(self, namespace: str = None) -> str:
        """List deployments."""
        try:
            deployments = self.client.list_deployments(namespace=namespace)

            if not deployments:
                return f"No deployments found{f' in {namespace}' if namespace else ''}."

            response = f"🚀 Deployments{f' in {namespace}' if namespace else ''}:\n" + "━" * 60 + "\n"

            for deploy in deployments:
                ready = deploy.get("ready_replicas", 0)
                desired = deploy.get("desired_replicas", 0)
                status_emoji = "✅" if ready == desired else "⏳"
                response += (
                    f"{status_emoji} {deploy.get('name', 'unknown'):40} "
                    f"{ready}/{desired}\n"
                )

            return response
        except Exception as e:
            return f"❌ Error listing deployments: {e}"

    def _handle_list_nodes(self) -> str:
        """List cluster nodes."""
        try:
            nodes = self.client.list_nodes()

            if not nodes:
                return "No nodes found in cluster."

            response = "🖥️  Cluster Nodes:\n" + "━" * 60 + "\n"

            for node in nodes:
                status = node.get("status", "Unknown")
                status_emoji = "✅" if status == "True" else "❌"
                response += (
                    f"{status_emoji} {node.get('name', 'unknown'):40} "
                    f"{node.get('address', 'N/A'):20}\n"
                )

            return response
        except Exception as e:
            return f"❌ Error listing nodes: {e}"

    def _handle_list_namespaces(self) -> str:
        """List all namespaces."""
        try:
            namespaces = self.client.list_namespaces()

            if not namespaces:
                return "No namespaces found."

            response = "🏷️  Namespaces:\n" + "━" * 60 + "\n"
            for ns in sorted(namespaces):
                response += f"  • {ns}\n"

            return response
        except Exception as e:
            return f"❌ Error listing namespaces: {e}"

    def _get_help_text(self) -> str:
        """Get help text."""
        return """
🤖 K3s Cluster Chatbot - Help
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Available Commands:
  • "health" / "status" - Show cluster health
  • "pods" / "containers" - List pods in cluster
  • "pods in <namespace>" - List pods in specific namespace
  • "logs <pod_name>" - Get logs from a pod
  • "deployments" - List deployments
  • "nodes" - List cluster nodes
  • "namespaces" - List all namespaces

Examples:
  > health
  > pods in kube-system
  > logs my-app-pod in default
  > deployments in monitoring

Type "exit" to quit.
""".strip()

    def _extract_namespace(self, query: str) -> str:
        """Extract namespace from query."""
        # Look for "in <namespace>" pattern
        match = re.search(r'\bin\s+(\w+)\b', query, re.IGNORECASE)
        if match:
            return match.group(1)
        return None

    def _extract_pod_name(self, query: str) -> str:
        """Extract pod name from query."""
        # Look for quoted strings or specific patterns
        match = re.search(r'"([^"]+)"', query)
        if match:
            return match.group(1)

        # Look for "logs <pod>" pattern
        match = re.search(r'logs\s+(\w+[a-z0-9-]*)', query, re.IGNORECASE)
        if match:
            return match.group(1)

        return None

    def run_interactive(self) -> None:
        """Run interactive chat loop."""
        print("\n🤖 K3s Cluster Chatbot")
        print("Type 'help' for available commands, 'exit' to quit.\n")

        try:
            while True:
                try:
                    user_input = input("You: ").strip()

                    if not user_input:
                        continue

                    if user_input.lower() in ["exit", "quit", "bye"]:
                        print("\nGoodbye! 👋")
                        break

                    response = self.handle_query(user_input)
                    print(f"\nBot: {response}\n")

                except KeyboardInterrupt:
                    print("\n\nGoodbye! 👋")
                    break
                except Exception as e:
                    logger.error(f"Error processing query: {e}")
                    print(f"\n❌ Error: {e}\n")

        finally:
            self.client.disconnect()


def main():
    """Main entry point."""
    try:
        # Create and run chatbot
        chatbot = K3sChatbot()

        if not chatbot.client.is_connected():
            print("❌ Failed to connect to MCP server.")
            print("Make sure the server is running with: python -m mcp_k3s_monitor")
            return 1

        chatbot.run_interactive()
        return 0

    except KeyboardInterrupt:
        print("\n\nInterrupted.")
        return 1
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        print(f"❌ Fatal error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
