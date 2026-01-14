# GitHub Webhook Agents

This document describes the webhook-based agent system for the MCP k3s Server.

## Overview

The agent system consists of 3 specialized agents that process GitHub webhooks and analyze Kubernetes cluster issues:

- **Feature Agent** - Analyzes feature requests and cluster capacity
- **Bug Agent** - Triages bugs and identifies root causes
- **Chore Agent** - Handles maintenance and operational tasks

## Architecture

```
GitHub Webhooks (HTTP)
        ↓
  FastAPI Server (/webhooks/github)
        ↓
  Signature Validation (HMAC-SHA256)
        ↓
  Label-Based Agent Routing
        ↓
  Agent Workflow (Async Background Task)
        ├─→ Query k3s Cluster (via MCP)
        ├─→ Analyze with Claude
        ├─→ Generate HTML Report
        ├─→ Post GitHub Comment
        └─→ Execute Local Workflow Script
```

## Configuration

Set environment variables in `.env`:

```bash
# GitHub Configuration
AGENT_GITHUB_TOKEN=ghp_xxxxx
AGENT_GITHUB_WEBHOOK_SECRET=your-webhook-secret
AGENT_GITHUB_REPO_OWNER=your-org
AGENT_GITHUB_REPO_NAME=your-repo

# Anthropic Configuration
AGENT_ANTHROPIC_API_KEY=sk-ant-xxxxx
AGENT_ANTHROPIC_MODEL=claude-3-5-sonnet-20241022

# MCP Server Configuration
AGENT_MCP_SERVER_COMMAND=python -m mcp_k3s_monitor
AGENT_MCP_TIMEOUT=30

# Webhook Server Configuration
AGENT_WEBHOOK_HOST=0.0.0.0
AGENT_WEBHOOK_PORT=8000

# Report and Workflow Directories
AGENT_REPORTS_OUTPUT_DIR=./reports
AGENT_WORKFLOWS_DIR=./workflows

# Logging
AGENT_LOG_LEVEL=INFO
```

## Running the Server

### Start MCP Server (in one terminal)
```bash
python -m mcp_k3s_monitor
```

### Start Webhook Server (in another terminal)
```bash
python -m mcp_k3s_monitor.webhooks
```

Or with uvicorn directly:
```bash
uvicorn mcp_k3s_monitor.webhooks.server:app --host 0.0.0.0 --port 8000
```

## GitHub Webhook Setup

1. Go to Repository Settings → Webhooks → Add webhook
2. Set **Payload URL**: `https://your-server.com/webhooks/github`
3. Set **Content type**: `application/json`
4. Set **Secret**: (same as `AGENT_GITHUB_WEBHOOK_SECRET`)
5. Select events:
   - Issues
   - Issue comments (optional)
6. Click **Add webhook**

## How Agents Work

### 1. Webhook Routing

Issues are routed to agents based on labels:

- **Feature Agent**: `feature`, `enhancement`, `feature-request`
- **Bug Agent**: `bug`, `error`, `issue`
- **Chore Agent**: `chore`, `maintenance`, `refactor`, `docs`

### 2. Agent Workflow

When an issue matches an agent's labels:

1. **Query Cluster** - Connects to MCP server to get:
   - Cluster health status
   - Pod information
   - Deployment status
   - Node information
   - Namespace listing
   - (Bug Agent only) Failed pod logs

2. **Analyze with Claude** - Sends cluster data + issue to Claude for analysis:
   - Generates structured JSON response
   - Includes recommendations, severity, risks, etc.

3. **Generate Report** - Creates HTML dashboard with:
   - Issue information
   - Analysis results
   - Cluster status metrics
   - Recommendations
   - (Bug Agent) Failed pods and logs
   - (Feature Agent) Capacity assessment
   - (Chore Agent) Current state assessment

4. **Post GitHub Comment** - Comments on issue with:
   - Summary
   - Recommendations
   - Link to HTML report

5. **Execute Workflow** - Runs local script:
   - **Feature**: `workflows/templates/feature_workflow.sh`
   - **Bug**: `workflows/templates/bug_workflow.py`
   - **Chore**: `workflows/templates/chore_workflow.sh`

## Example Usage

### Create a Feature Request Issue

```markdown
**Title:** Add monitoring dashboard

**Labels:** feature, enhancement

**Body:**
We need a dashboard to monitor cluster health in real-time.
```

**Result:**
1. Webhook triggers Feature Agent
2. Agent queries cluster capacity
3. Claude generates implementation plan
4. HTML report generated in `./reports/`
5. Comment posted with recommendations
6. Workflow script executes

### Create a Bug Report Issue

```markdown
**Title:** Pods crashing in production

**Labels:** bug, urgent

**Body:**
Multiple pods are crash-looping with OOM errors.
```

**Result:**
1. Webhook triggers Bug Agent
2. Agent queries failed pods and their logs
3. Claude performs triage and identifies root cause
4. HTML report generated with debugging steps
5. Comment posted with severity and recommendations
6. Workflow script executes (can auto-restart pods)

### Create a Maintenance Task

```markdown
**Title:** Clean up old resources

**Labels:** chore, maintenance

**Body:**
Review cluster for unused resources and optimize configuration.
```

**Result:**
1. Webhook triggers Chore Agent
2. Agent assesses current state
3. Claude recommends optimizations
4. HTML report generated with action plan
5. Comment posted with recommendations
6. Workflow script executes (cleanup tasks)

## Workflow Scripts

Workflow scripts receive cluster context and analysis as JSON:

```bash
# scripts receive $1 = path to JSON file
VARS_FILE="$1"

# Access variables with jq
ISSUE_NUMBER=$(jq -r '.issue.number' "$VARS_FILE")
SEVERITY=$(jq -r '.analysis.severity' "$VARS_FILE")
```

### Custom Workflows

To customize workflow behavior, edit scripts in:
- `src/mcp_k3s_monitor/workflows/templates/feature_workflow.sh`
- `src/mcp_k3s_monitor/workflows/templates/bug_workflow.py`
- `src/mcp_k3s_monitor/workflows/templates/chore_workflow.sh`

## Reports

HTML reports are generated in `./reports/` directory with naming:
```
{agent_type}_issue_{issue_number}_{timestamp}.html
```

Example: `bug_issue_42_1705358023.html`

Reports include:
- Issue information
- Agent analysis results
- Cluster status metrics
- Recommendations
- Relevant cluster data (pods, deployments, nodes, etc.)

## Troubleshooting

### Webhook not triggering

1. Check webhook delivery in GitHub Settings → Webhooks
2. Verify signature secret matches `AGENT_GITHUB_WEBHOOK_SECRET`
3. Check webhook server logs

### Agent not processing webhook

1. Verify issue has correct label for agent
2. Check webhook server is running
3. Review logs for errors

### Report not generated

1. Ensure `AGENT_REPORTS_OUTPUT_DIR` exists
2. Check write permissions
3. Review logs for Jinja2 template errors

### MCP connection fails

1. Verify MCP server is running
2. Check `AGENT_MCP_SERVER_COMMAND` is correct
3. Ensure kubeconfig is accessible

### Claude API errors

1. Verify `AGENT_ANTHROPIC_API_KEY` is valid
2. Check API quota and rate limits
3. Verify model name is correct

## Development

### Testing

Run webhook validator tests:
```bash
pytest tests/unit/webhooks/test_validators.py -v
```

### Extending

To add a new agent type:

1. Create new class in `agents/new_agent.py`:
   ```python
   from mcp_k3s_monitor.agents.base_agent import BaseAgent

   class NewAgent(BaseAgent):
       def get_agent_name(self) -> str:
           return "New Agent"

       # Implement abstract methods...
   ```

2. Register in `agents/agent_factory.py`:
   ```python
   elif agent_type == "new":
       return NewAgent(self.config)
   ```

3. Update label mapping in `.env`:
   ```bash
   AGENT_AGENT_LABELS='{"new": ["new-label"]}'
   ```

4. Create workflow template:
   ```bash
   src/mcp_k3s_monitor/workflows/templates/new_workflow.sh
   ```

5. Create HTML report template:
   ```html
   src/mcp_k3s_monitor/reports/templates/new_report.html
   ```

## Performance

- **Webhook processing**: Async background tasks (non-blocking)
- **MCP queries**: ~1-2 seconds per query
- **Claude analysis**: ~3-5 seconds per analysis
- **Report generation**: <1 second
- **Total time per webhook**: ~10-15 seconds

## Security

- GitHub signatures validated with HMAC-SHA256
- Secrets stored in `SecretStr` (not logged)
- API keys loaded from environment
- Input validation on all payloads
- Workflow scripts run in isolated subprocess
- Configurable timeout for all operations

## License

Same as MCP k3s Server
