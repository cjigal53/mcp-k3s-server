#!/usr/bin/env python3
"""
Continuous Monitoring Loop Example

Demonstrates how to use MCPChatbotClient to continuously monitor a k3s cluster
and report status changes.

Usage:
    python examples/mcp_monitoring_loop.py --interval 30 --namespace default
"""

import sys
import time
import argparse
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mcp_k3s_monitor.chatbot import MCPChatbotClient


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class ClusterMonitor:
    """Continuous k3s cluster monitor."""

    def __init__(self, namespace=None, check_interval=30):
        """
        Initialize monitor.

        Args:
            namespace: Kubernetes namespace to monitor (None = all).
            check_interval: Seconds between checks.
        """
        self.client = MCPChatbotClient()
        self.namespace = namespace
        self.check_interval = check_interval
        self.previous_state = {}

    def run(self, duration_minutes=None):
        """
        Run monitoring loop.

        Args:
            duration_minutes: How long to monitor (None = forever).
        """
        start_time = time.time()
        max_duration = (duration_minutes * 60) if duration_minutes else float('inf')

        try:
            print(f"🔍 Starting cluster monitoring...")
            print(f"   Namespace: {self.namespace or 'all'}")
            print(f"   Interval: {self.check_interval}s")
            if duration_minutes:
                print(f"   Duration: {duration_minutes}m")
            print()

            iteration = 0
            while (time.time() - start_time) < max_duration:
                iteration += 1
                print(f"[{iteration}] Checking cluster at {time.strftime('%H:%M:%S')}...")

                try:
                    self._check_health()
                    self._check_pods()
                    self._check_deployments()

                except Exception as e:
                    logger.error(f"Error during check: {e}")

                print(f"    ✓ Check complete. Next check in {self.check_interval}s\n")
                time.sleep(self.check_interval)

        except KeyboardInterrupt:
            print("\n\n⏹️  Monitoring stopped by user")
        finally:
            self.client.disconnect()

    def _check_health(self):
        """Check cluster health."""
        try:
            health = self.client.get_cluster_health()

            status = health.get('status', 'unknown')
            nodes_ready = health.get('nodes_ready', 0)
            nodes_total = health.get('nodes_count', 0)
            pods_running = health.get('pods_running', 0)
            pods_failed = health.get('pods_failed', 0)

            # Check for state changes
            current_state = {
                'status': status,
                'nodes_ready': nodes_ready,
                'pods_failed': pods_failed,
            }

            if 'health' in self.previous_state:
                prev = self.previous_state['health']
                if prev != current_state:
                    logger.warning("⚠️  Cluster state changed!")

            self.previous_state['health'] = current_state

            print(f"  Health: {status} | Nodes: {nodes_ready}/{nodes_total} | "
                  f"Pods: {pods_running} running, {pods_failed} failed")

        except Exception as e:
            logger.error(f"Failed to check health: {e}")

    def _check_pods(self):
        """Check pod status."""
        try:
            pods = self.client.list_pods(namespace=self.namespace)

            if not pods:
                print(f"  Pods: No pods found" + (f" in {self.namespace}" if self.namespace else ""))
                return

            running = sum(1 for p in pods if p.get('status') == 'Running')
            pending = sum(1 for p in pods if p.get('status') == 'Pending')
            failed = sum(1 for p in pods if p.get('status') == 'Failed')
            other = len(pods) - running - pending - failed

            print(f"  Pods: {running} running, {pending} pending, {failed} failed, {other} other")

            # Log any failed pods
            if failed > 0:
                failed_pods = [p for p in pods if p.get('status') == 'Failed']
                for pod in failed_pods[:5]:  # Show first 5
                    logger.error(f"    ❌ Failed pod: {pod.get('name')} in {pod.get('namespace')}")

        except Exception as e:
            logger.error(f"Failed to check pods: {e}")

    def _check_deployments(self):
        """Check deployment status."""
        try:
            deployments = self.client.list_deployments(namespace=self.namespace)

            if not deployments:
                print(f"  Deployments: No deployments found" + (f" in {self.namespace}" if self.namespace else ""))
                return

            ready = sum(
                1 for d in deployments
                if d.get('ready_replicas') == d.get('desired_replicas')
            )
            not_ready = len(deployments) - ready

            print(f"  Deployments: {ready} ready, {not_ready} not ready")

            # Log any not-ready deployments
            if not_ready > 0:
                for d in deployments:
                    if d.get('ready_replicas') != d.get('desired_replicas'):
                        logger.warning(
                            f"    ⚠️  {d.get('name')}: "
                            f"{d.get('ready_replicas')}/{d.get('desired_replicas')} ready"
                        )

        except Exception as e:
            logger.error(f"Failed to check deployments: {e}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Continuous k3s cluster monitoring"
    )
    parser.add_argument(
        "--namespace",
        help="Kubernetes namespace to monitor (default: all)",
        default=None,
    )
    parser.add_argument(
        "--interval",
        type=int,
        help="Check interval in seconds (default: 30)",
        default=30,
    )
    parser.add_argument(
        "--duration",
        type=int,
        help="Monitor for N minutes (default: forever)",
        default=None,
    )

    args = parser.parse_args()

    try:
        monitor = ClusterMonitor(
            namespace=args.namespace,
            check_interval=args.interval,
        )
        monitor.run(duration_minutes=args.duration)
        return 0
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
