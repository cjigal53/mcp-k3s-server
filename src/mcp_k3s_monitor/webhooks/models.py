"""Webhook payload models."""

from pydantic import BaseModel
from typing import Optional


class WebhookResponse(BaseModel):
    """Response model for webhook endpoints."""

    status: str  # accepted, skipped, error
    message: str
    webhook_id: Optional[str] = None
