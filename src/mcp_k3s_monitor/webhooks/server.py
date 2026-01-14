"""FastAPI webhook server for GitHub integration."""

from fastapi import FastAPI, Request, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse
import logging
from contextlib import asynccontextmanager

from mcp_k3s_monitor.agents.config import AgentSystemConfig
from mcp_k3s_monitor.agents.agent_factory import AgentFactory
from mcp_k3s_monitor.webhooks import routes

logger = logging.getLogger(__name__)

# Global state
agents = {}
config = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    global agents, config

    # Startup
    logger.info("Starting webhook server...")
    config = AgentSystemConfig()

    # Initialize agents
    factory = AgentFactory(config)
    agents = {
        "feature": factory.create_agent("feature"),
        "bug": factory.create_agent("bug"),
        "chore": factory.create_agent("chore"),
    }

    logger.info("Agents initialized successfully")

    yield

    # Shutdown
    logger.info("Shutting down webhook server...")
    for agent_type, agent in agents.items():
        try:
            agent.cleanup()
        except Exception as e:
            logger.error(f"Error cleaning up {agent_type} agent: {e}")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    app = FastAPI(
        title="MCP k3s Agent Webhook Server",
        description="GitHub webhook receiver for k3s monitoring agents",
        version="1.0.0",
        lifespan=lifespan,
    )

    # Include routes
    app.include_router(
        routes.router,
        prefix="/webhooks",
        tags=["webhooks"],
    )

    # Health check endpoint
    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "agents": list(agents.keys())}

    @app.get("/")
    async def root():
        return {
            "name": "MCP k3s Agent Webhook Server",
            "status": "running",
            "agents": list(agents.keys()),
        }

    return app


def get_agents():
    """Get current agents."""
    return agents


def get_config():
    """Get current config."""
    return config
