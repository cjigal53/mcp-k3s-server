"""GitHub webhook routes."""

from fastapi import APIRouter, Request, BackgroundTasks, HTTPException, Header, Depends
from typing import Optional
import logging

from mcp_k3s_monitor.webhooks.models import WebhookResponse
from mcp_k3s_monitor.webhooks.validators import validate_github_signature
from mcp_k3s_monitor.webhooks.server import get_agents, get_config

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/github", response_model=WebhookResponse)
async def github_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_github_event: Optional[str] = Header(None),
    x_hub_signature_256: Optional[str] = Header(None),
    agents=Depends(get_agents),
    config=Depends(get_config),
):
    """
    Receive GitHub webhooks and route to appropriate agent.

    Validates signature, determines agent based on labels, and processes in background.
    """
    # Read raw body for signature validation
    body = await request.body()

    # Validate signature
    if not validate_github_signature(
        payload=body,
        signature=x_hub_signature_256,
        secret=config.github_webhook_secret.get_secret_value(),
    ):
        raise HTTPException(status_code=401, detail="Invalid signature")

    # Parse JSON payload
    payload = await request.json()

    # Only process issue events
    if x_github_event not in ["issues", "issue_comment"]:
        return WebhookResponse(
            status="skipped",
            message=f"Event type {x_github_event} not handled",
        )

    # Determine which agent should handle this
    agent = _route_to_agent(payload, agents)

    if agent is None:
        return WebhookResponse(
            status="skipped",
            message="No matching agent for issue labels",
        )

    # Process in background
    background_tasks.add_task(
        _process_webhook_background,
        agent=agent,
        event_type=x_github_event,
        payload=payload,
    )

    return WebhookResponse(
        status="accepted",
        message=f"Webhook queued for processing by {agent.get_agent_name()}",
    )


def _route_to_agent(payload: dict, agents: dict):
    """Determine which agent should handle this webhook."""
    issue = payload.get("issue", {})
    labels = {label["name"] for label in issue.get("labels", [])}

    # Check each agent's label configuration
    for agent_type, agent in agents.items():
        if agent._should_process_issue(issue):
            return agent

    return None


async def _process_webhook_background(
    agent,
    event_type: str,
    payload: dict,
):
    """Process webhook in background task."""
    try:
        logger.info(f"Background processing webhook with {agent.get_agent_name()}")
        result = await agent.process_webhook(event_type, payload)
        logger.info(f"Webhook processing result: {result}")
    except Exception as e:
        logger.error(f"Error in background webhook processing: {e}", exc_info=True)
