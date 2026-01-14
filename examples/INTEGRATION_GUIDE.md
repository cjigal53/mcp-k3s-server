# K3s MCP Chatbot Integration Guide

This guide explains how to use the MCPChatbotClient and related tools to integrate the MCP k3s monitoring server with chatbot applications.

## Prerequisites

1. **Python 3.9+**
2. **k3s cluster** running and accessible
3. **kubeconfig** file configured (~/.kube/config)
4. **MCP server** running

## Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Verify kubeconfig is set up
kubectl cluster-info
```

## Quick Start

### 1. Start the MCP Server

```bash
# Terminal 1: Start the MCP server
python -m mcp_k3s_monitor
```

### 2. Interactive Chatbot

```bash
# Terminal 2: Run the interactive chatbot
python examples/claude_chatbot_integration.py
```

#### Example Interactions:

```
You: health
Bot: 🏥 Cluster Health Status:
     Status: healthy
     Nodes: 3/3 ready
     Pods: 47 running, 2 pending, 0 failed
     Services: 8
     Deployments: 12

You: pods in default
Bot: 📦 Pods in default:
     ✅ nginx-deploy-789... Running 1/1
     ✅ redis-cache-567... Running 1/1

You: logs "my-app-pod" in default
Bot: 📄 Logs for my-app-pod (default):
     [2024-01-12T10:30:45] Server started
     [2024-01-12T10:30:46] Connected to database
     ...

You: nodes
Bot: 🖥️ Cluster Nodes:
     ✅ k3s-master-1    192.168.1.10
     ✅ k3s-worker-1    192.168.1.11
     ✅ k3s-worker-2    192.168.1.12

You: exit
Bot: Goodbye! 👋
```

## Programmatic Usage

### Using MCPChatbotClient

```python
from src.mcp_k3s_monitor.chatbot import MCPChatbotClient

# Create client
client = MCPChatbotClient()

# Get cluster health
health = client.get_cluster_health()
print(f"Cluster status: {health['status']}")
print(f"Nodes ready: {health['nodes_ready']}/{health['nodes_count']}")

# List pods in namespace
pods = client.list_pods(namespace="default")
for pod in pods:
    print(f"{pod['name']}: {pod['status']}")

# Get pod logs
logs = client.get_pod_logs(
    pod_name="my-app",
    namespace="default",
    lines=50
)
print(logs)

# List deployments
deployments = client.list_deployments(namespace="default")
for deploy in deployments:
    ready = deploy['ready_replicas']
    desired = deploy['desired_replicas']
    print(f"{deploy['name']}: {ready}/{desired} ready")

# Cleanup
client.disconnect()
```

### Using K3sClient

The K3sClient provides a high-level interface directly to your k3s cluster (without MCP server):

```python
from src.mcp_k3s_monitor.kubernetes.k3s_client import K3sClient, K3sClientError

try:
    client = K3sClient()

    # Get cluster health
    health = client.get_cluster_health()
    print(f"Status: {health.status}")
    print(f"Nodes: {health.nodes_ready}/{health.nodes_count}")

    # List pods
    pods = client.list_pods(namespace="default")
    for pod in pods:
        print(f"{pod.name}: {pod.status}")

    # Get logs
    logs = client.get_pod_logs(
        pod_name="my-app",
        namespace="default",
        lines=100
    )

    # List nodes
    nodes = client.list_nodes()
    for node in nodes:
        print(f"{node['name']}: {node['status']}")

except K3sClientError as e:
    print(f"Error: {e}")
```

## Example Scripts

### 1. Continuous Monitoring Loop

Monitor cluster health continuously and report state changes:

```bash
# Monitor all pods every 30 seconds for 10 minutes
python examples/mcp_monitoring_loop.py --duration 10

# Monitor specific namespace every 60 seconds
python examples/mcp_monitoring_loop.py --namespace kube-system --interval 60
```

### 2. Resource Search

Search and filter resources:

```bash
# Find all pods with high restart counts
python examples/mcp_resource_search.py --high-restart 5

# Find unhealthy pods
python examples/mcp_resource_search.py --unhealthy

# Search pods by image
python examples/mcp_resource_search.py --search-pods nginx

# Show pods by namespace
python examples/mcp_resource_search.py --by-namespace

# Export cluster snapshot
python examples/mcp_resource_search.py --export-json cluster_snapshot.json
```

## Configuration

### Environment Variables

```bash
# .env file
KUBECONFIG=/path/to/kubeconfig
LOG_LEVEL=INFO
MCP_SERVER_TIMEOUT=30
```

### Kubeconfig Locations

The client checks for kubeconfig in this order:
1. `KUBECONFIG` environment variable
2. `~/.kube/config`
3. Default location

To use a custom kubeconfig:

```bash
export KUBECONFIG=/path/to/custom/kubeconfig
python examples/claude_chatbot_integration.py
```

Or programmatically:

```python
from src.mcp_k3s_monitor.kubernetes.k3s_client import K3sClient

client = K3sClient(kubeconfig_path="/path/to/kubeconfig")
```

## Troubleshooting

### Connection Issues

**Problem**: "Failed to connect to MCP server"

**Solution**: Make sure the server is running:
```bash
python -m mcp_k3s_monitor
```

### Kubeconfig Not Found

**Problem**: "Failed to load kubeconfig"

**Solution**:
```bash
# Check kubeconfig location
echo $KUBECONFIG
ls ~/.kube/config

# Set explicit path
export KUBECONFIG=~/.kube/config
```

### Timeout Errors

**Problem**: "No response from MCP server (timeout)"

**Solution**: Increase timeout or check server logs:
```python
client = MCPChatbotClient(timeout=60)  # 60 second timeout
```

### Pod Logs Not Available

**Problem**: "Error getting pod logs: not found"

**Solution**: Verify pod name and namespace:
```bash
# List all pods
kubectl get pods --all-namespaces

# Then use exact name
python examples/claude_chatbot_integration.py
> logs "exact-pod-name" in namespace
```

## Integration with Claude Chatbot

To integrate with Claude or other AI chatbots:

```python
from src.mcp_k3s_monitor.chatbot import MCPChatbotClient

class K3sAssistant:
    def __init__(self):
        self.client = MCPChatbotClient()

    def process_user_query(self, query: str) -> str:
        """Process natural language query and return response"""
        if "health" in query.lower():
            health = self.client.get_cluster_health()
            return f"Cluster is {health['status']}"
        elif "pods" in query.lower():
            pods = self.client.list_pods()
            return f"Found {len(pods)} pods"
        # ... more handlers

# Use with Claude
assistant = K3sAssistant()
response = assistant.process_user_query("What is cluster health?")
```

## Testing

Run the test suite:

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/unit/test_chatbot_client.py -v

# Run with coverage
pytest --cov=src tests/
```

## Performance Tips

1. **Use namespaces**: Limit queries to specific namespaces to reduce data
   ```python
   pods = client.list_pods(namespace="default")
   ```

2. **Cache results**: The client caches tool list for 60 seconds
   ```python
   # Uses cache
   tools = client.list_tools(use_cache=True)
   ```

3. **Batch operations**: Group multiple queries in one function

4. **Use label selectors**: Filter at the API level
   ```python
   pods = client.list_pods(label_selector="app=myapp")
   ```

## API Reference

### MCPChatbotClient Methods

- `connect()` - Connect to MCP server
- `disconnect()` - Disconnect from server
- `is_connected()` - Check connection status
- `list_tools()` - Get available tools
- `call_tool(name, **kwargs)` - Call a tool
- `get_cluster_health()` - Get cluster status
- `list_pods(namespace, label_selector)` - List pods
- `get_pod_logs(pod_name, namespace, lines)` - Get logs
- `list_deployments(namespace)` - List deployments
- `list_nodes()` - List cluster nodes
- `list_namespaces()` - List namespaces

### K3sClient Methods

- `get_cluster_health()` - Get cluster health
- `list_pods()` - List pods with filtering
- `get_pod_logs()` - Get pod logs
- `list_deployments()` - List deployments
- `list_services()` - List services
- `list_nodes()` - List nodes
- `list_namespaces()` - List namespaces
- `get_resource_usage()` - Get resource usage

## Next Steps

1. **Integrate with Claude**: Use the client in your Claude integration
2. **Create custom tools**: Extend the MCP server with custom commands
3. **Add persistence**: Store monitoring history in a database
4. **Set up alerts**: Create alerting rules for cluster issues
5. **Build dashboard**: Create a web UI for cluster monitoring

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review example scripts
3. Check server logs: `python -m mcp_k3s_monitor --verbose`
