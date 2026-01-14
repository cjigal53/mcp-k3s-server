"""Local workflow script executor."""

import subprocess
import json
import logging
from pathlib import Path
from typing import Dict, Any
import tempfile
import asyncio

from mcp_k3s_monitor.agents.config import AgentSystemConfig

logger = logging.getLogger(__name__)


class WorkflowExecutor:
    """Execute local workflow scripts (bash/python)."""

    def __init__(self, config: AgentSystemConfig):
        self.config = config
        self.workflows_dir = config.workflows_dir
        self.workflows_dir.mkdir(parents=True, exist_ok=True)
        self.timeout = config.workflow_timeout

    async def execute(
        self,
        template_path: str,
        variables: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Execute workflow script with variables.

        Args:
            template_path: Path to script template
            variables: Variables to pass to script (as JSON)

        Returns:
            Execution result
        """
        try:
            template_path = Path(template_path)

            if not template_path.exists():
                logger.warning(f"Workflow template not found: {template_path}")
                return {"status": "skipped", "reason": "Template not found"}

            # Determine script type
            suffix = template_path.suffix

            if suffix == ".sh":
                result = await self._execute_bash(template_path, variables)
            elif suffix == ".py":
                result = await self._execute_python(template_path, variables)
            else:
                raise ValueError(f"Unsupported script type: {suffix}")

            return result

        except Exception as e:
            logger.error(f"Error executing workflow: {e}", exc_info=True)
            return {"status": "error", "error": str(e)}

    async def _execute_bash(
        self,
        script_path: Path,
        variables: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute bash script."""
        # Create temp file with variables as JSON
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(variables, f)
            vars_file = f.name

        try:
            # Run script with variables file as argument
            process = await asyncio.create_subprocess_exec(
                "bash",
                str(script_path),
                vars_file,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.timeout,
            )

            return {
                "status": "success" if process.returncode == 0 else "failed",
                "returncode": process.returncode,
                "stdout": stdout.decode("utf-8"),
                "stderr": stderr.decode("utf-8"),
            }

        finally:
            # Cleanup temp file
            Path(vars_file).unlink(missing_ok=True)

    async def _execute_python(
        self,
        script_path: Path,
        variables: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute Python script."""
        # Create temp file with variables as JSON
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(variables, f)
            vars_file = f.name

        try:
            # Run script with variables file as argument
            process = await asyncio.create_subprocess_exec(
                "python",
                str(script_path),
                vars_file,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.timeout,
            )

            return {
                "status": "success" if process.returncode == 0 else "failed",
                "returncode": process.returncode,
                "stdout": stdout.decode("utf-8"),
                "stderr": stderr.decode("utf-8"),
            }

        finally:
            # Cleanup temp file
            Path(vars_file).unlink(missing_ok=True)
