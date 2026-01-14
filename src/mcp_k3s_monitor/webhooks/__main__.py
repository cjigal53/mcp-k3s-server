"""Run webhook server."""

import uvicorn
import logging
import sys

from mcp_k3s_monitor.agents.config import AgentSystemConfig
from mcp_k3s_monitor.webhooks.server import create_app

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


def main():
    try:
        config = AgentSystemConfig()
        app = create_app()

        logger.info(
            f"Starting webhook server on {config.webhook_host}:{config.webhook_port}"
        )

        uvicorn.run(
            app,
            host=config.webhook_host,
            port=config.webhook_port,
            log_level=config.log_level.lower(),
        )
    except Exception as e:
        logger.error(f"Failed to start webhook server: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
