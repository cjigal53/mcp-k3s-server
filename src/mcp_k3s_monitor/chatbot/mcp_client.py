"""
MCP Chatbot Client - Communicates with MCP k3s monitoring server via stdio.

Provides a client interface for chatbot applications to interact with the MCP server
using the standard MCP protocol over stdio.
"""

import json
import subprocess
import logging
import time
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict


logger = logging.getLogger(__name__)


@dataclass
class MCPMessage:
    """MCP protocol message"""
    jsonrpc: str = "2.0"
    method: str = ""
    params: Dict[str, Any] = None
    id: int = 1

    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps({
            "jsonrpc": self.jsonrpc,
            "method": self.method,
            "params": self.params or {},
            "id": self.id,
        })


class MCPChatbotClientError(Exception):
    """Base exception for MCPChatbotClient"""
    pass


class MCPChatbotClient:
    """
    Client for communicating with MCP k3s monitoring server.

    Manages subprocess communication with the server using the MCP protocol.
    """

    def __init__(
        self,
        server_command: str = "python -m mcp_k3s_monitor",
        timeout: int = 30,
        auto_connect: bool = True,
    ):
        """
        Initialize MCPChatbotClient.

        Args:
            server_command: Command to start the MCP server.
            timeout: Timeout for server operations in seconds.
            auto_connect: If True, connect to server on initialization.

        Raises:
            MCPChatbotClientError: If auto_connect is True and connection fails.
        """
        self.server_command = server_command
        self.timeout = timeout
        self.process = None
        self.request_id = 0
        self._tools_cache = None
        self._tools_cache_time = 0

        if auto_connect:
            self.connect()

    def connect(self) -> bool:
        """
        Connect to MCP server by starting the process.

        Returns:
            True if connection successful.

        Raises:
            MCPChatbotClientError: If connection fails.
        """
        try:
            self.process = subprocess.Popen(
                self.server_command.split(),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
            )
            logger.info(f"Connected to MCP server: {self.server_command}")
            return True
        except Exception as e:
            raise MCPChatbotClientError(f"Failed to connect to MCP server: {e}")

    def disconnect(self) -> None:
        """Disconnect from MCP server."""
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            finally:
                self.process = None
            logger.info("Disconnected from MCP server")

    def is_connected(self) -> bool:
        """Check if connected to server."""
        return self.process is not None and self.process.poll() is None

    def _get_next_request_id(self) -> int:
        """Get next request ID."""
        self.request_id += 1
        return self.request_id

    def _send_request(self, method: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Send request to server and get response.

        Args:
            method: MCP method name.
            params: Method parameters.

        Returns:
            Response dictionary.

        Raises:
            MCPChatbotClientError: If request fails.
        """
        if not self.is_connected():
            raise MCPChatbotClientError("Not connected to MCP server")

        try:
            request_id = self._get_next_request_id()
            message = MCPMessage(
                method=method,
                params=params or {},
                id=request_id,
            )

            # Send request
            request_json = message.to_json() + "\n"
            self.process.stdin.write(request_json)
            self.process.stdin.flush()

            # Read response with timeout
            start_time = time.time()
            response_line = ""

            while time.time() - start_time < self.timeout:
                if self.process.stdout.readable():
                    response_line = self.process.stdout.readline()
                    if response_line:
                        break
                time.sleep(0.01)

            if not response_line:
                raise MCPChatbotClientError("No response from MCP server (timeout)")

            response = json.loads(response_line)
            return response

        except json.JSONDecodeError as e:
            raise MCPChatbotClientError(f"Invalid JSON response from server: {e}")
        except Exception as e:
            raise MCPChatbotClientError(f"Request failed: {e}")

    def list_tools(self, use_cache: bool = True) -> List[Dict[str, Any]]:
        """
        Get list of available tools from server.

        Args:
            use_cache: If True, cache tools for 60 seconds.

        Returns:
            List of tool definitions.
        """
        # Check cache
        if use_cache and self._tools_cache:
            if time.time() - self._tools_cache_time < 60:
                return self._tools_cache

        response = self._send_request("tools/list")

        if "result" in response:
            tools = response["result"].get("tools", [])
            self._tools_cache = tools
            self._tools_cache_time = time.time()
            return tools

        raise MCPChatbotClientError(f"Failed to list tools: {response}")

    def call_tool(
        self,
        tool_name: str,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Call a tool on the MCP server.

        Args:
            tool_name: Name of the tool to call.
            **kwargs: Tool arguments.

        Returns:
            Tool result dictionary.

        Raises:
            MCPChatbotClientError: If tool call fails.
        """
        response = self._send_request(
            "tools/call",
            {
                "name": tool_name,
                "arguments": kwargs,
            },
        )

        if "result" in response:
            return response["result"]
        elif "error" in response:
            raise MCPChatbotClientError(f"Tool error: {response['error']}")

        raise MCPChatbotClientError(f"Unexpected response: {response}")

    def get_cluster_health(self) -> Dict[str, Any]:
        """
        Get cluster health status.

        Returns:
            Cluster health information.
        """
        return self.call_tool("get_cluster_health")

    def list_pods(
        self,
        namespace: Optional[str] = None,
        label_selector: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        List pods.

        Args:
            namespace: Kubernetes namespace.
            label_selector: Label selector for filtering.

        Returns:
            List of pod information.
        """
        params = {}
        if namespace:
            params["namespace"] = namespace
        if label_selector:
            params["label_selector"] = label_selector

        return self.call_tool("list_pods", **params)

    def get_pod_logs(
        self,
        pod_name: str,
        namespace: str,
        lines: int = 50,
    ) -> str:
        """
        Get pod logs.

        Args:
            pod_name: Pod name.
            namespace: Pod namespace.
            lines: Number of log lines.

        Returns:
            Pod logs as string.
        """
        return self.call_tool(
            "get_pod_logs",
            pod_name=pod_name,
            namespace=namespace,
            lines=lines,
        )

    def list_deployments(self, namespace: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List deployments.

        Args:
            namespace: Kubernetes namespace.

        Returns:
            List of deployment information.
        """
        params = {}
        if namespace:
            params["namespace"] = namespace

        return self.call_tool("list_deployments", **params)

    def list_nodes(self) -> List[Dict[str, Any]]:
        """
        List cluster nodes.

        Returns:
            List of node information.
        """
        return self.call_tool("list_nodes")

    def list_namespaces(self) -> List[str]:
        """
        List all namespaces.

        Returns:
            List of namespace names.
        """
        return self.call_tool("list_namespaces")
