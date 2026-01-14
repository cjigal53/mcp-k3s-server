#!/usr/bin/env python3
"""
Resource Search Example

Demonstrates how to search and filter Kubernetes resources using MCPChatbotClient.

Usage:
    python examples/mcp_resource_search.py --search-pods
    python examples/mcp_resource_search.py --export-json
"""

import sys
import json
import argparse
import logging
from pathlib import Path
from typing import List, Dict, Any

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mcp_k3s_monitor.chatbot import MCPChatbotClient


logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class ResourceSearcher:
    """Search and analyze Kubernetes resources."""

    def __init__(self):
        """Initialize searcher with MCP client."""
        self.client = MCPChatbotClient()

    def search_pods_by_image(self, image_pattern: str) -> List[Dict[str, Any]]:
        """
        Find all pods using a specific image.

        Args:
            image_pattern: Image name or pattern to search for.

        Returns:
            List of matching pods.
        """
        try:
            all_pods = self.client.list_pods()

            matching_pods = [
                pod for pod in all_pods
                if image_pattern.lower() in pod.get('image', '').lower()
            ]

            return matching_pods
        except Exception as e:
            logger.error(f"Error searching pods: {e}")
            return []

    def find_unhealthy_pods(self) -> List[Dict[str, Any]]:
        """
        Find all pods that are not in Running state.

        Returns:
            List of unhealthy pods.
        """
        try:
            all_pods = self.client.list_pods()

            unhealthy = [
                pod for pod in all_pods
                if pod.get('status') != 'Running'
            ]

            return unhealthy
        except Exception as e:
            logger.error(f"Error searching pods: {e}")
            return []

    def find_high_restart_pods(self, threshold: int = 5) -> List[Dict[str, Any]]:
        """
        Find pods that have restarted more than threshold times.

        Args:
            threshold: Restart count threshold.

        Returns:
            List of pods with high restart counts.
        """
        try:
            all_pods = self.client.list_pods()

            high_restart = [
                pod for pod in all_pods
                if pod.get('restarts', 0) > threshold
            ]

            return high_restart
        except Exception as e:
            logger.error(f"Error searching pods: {e}")
            return []

    def get_pods_by_namespace(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Organize pods by namespace.

        Returns:
            Dictionary with namespaces as keys and pod lists as values.
        """
        try:
            all_pods = self.client.list_pods()
            organized = {}

            for pod in all_pods:
                ns = pod.get('namespace', 'unknown')
                if ns not in organized:
                    organized[ns] = []
                organized[ns].append(pod)

            return organized
        except Exception as e:
            logger.error(f"Error organizing pods: {e}")
            return {}

    def export_cluster_snapshot(self, output_file: Path) -> bool:
        """
        Export complete cluster snapshot to JSON file.

        Args:
            output_file: Output file path.

        Returns:
            True if successful.
        """
        try:
            snapshot = {
                "timestamp": str(Path(output_file).parent / "snapshot.json"),
                "cluster_health": self.client.get_cluster_health(),
                "pods": self.client.list_pods(),
                "deployments": self.client.list_deployments(),
                "nodes": self.client.list_nodes(),
                "namespaces": self.client.list_namespaces(),
            }

            with open(output_file, 'w') as f:
                json.dump(snapshot, f, indent=2, default=str)

            logger.info(f"✅ Exported cluster snapshot to {output_file}")
            return True
        except Exception as e:
            logger.error(f"Failed to export snapshot: {e}")
            return False

    def print_pods_by_image(self, image_pattern: str) -> None:
        """Print pods using specific image."""
        print(f"\n🔍 Searching for pods with image: {image_pattern}\n")

        pods = self.search_pods_by_image(image_pattern)

        if not pods:
            print(f"No pods found with image pattern '{image_pattern}'")
            return

        print(f"Found {len(pods)} pod(s):\n")
        print(f"{'Name':<40} {'Namespace':<15} {'Status':<10} {'Image'}")
        print("─" * 90)

        for pod in pods:
            print(
                f"{pod.get('name', 'N/A'):<40} "
                f"{pod.get('namespace', 'N/A'):<15} "
                f"{pod.get('status', 'N/A'):<10} "
                f"{pod.get('image', 'N/A')}"
            )

    def print_unhealthy_pods(self) -> None:
        """Print all unhealthy pods."""
        print("\n⚠️  Unhealthy Pods (not Running)\n")

        pods = self.find_unhealthy_pods()

        if not pods:
            print("All pods are healthy!")
            return

        print(f"Found {len(pods)} unhealthy pod(s):\n")
        print(f"{'Name':<40} {'Namespace':<15} {'Status':<15}")
        print("─" * 70)

        for pod in pods:
            print(
                f"{pod.get('name', 'N/A'):<40} "
                f"{pod.get('namespace', 'N/A'):<15} "
                f"{pod.get('status', 'N/A'):<15}"
            )

    def print_high_restart_pods(self, threshold: int = 5) -> None:
        """Print pods with high restart counts."""
        print(f"\n🔄 Pods with >{threshold} Restarts\n")

        pods = self.find_high_restart_pods(threshold)

        if not pods:
            print(f"No pods with more than {threshold} restarts")
            return

        print(f"Found {len(pods)} pod(s):\n")
        print(f"{'Name':<40} {'Namespace':<15} {'Restarts':<10}")
        print("─" * 65)

        for pod in pods:
            print(
                f"{pod.get('name', 'N/A'):<40} "
                f"{pod.get('namespace', 'N/A'):<15} "
                f"{pod.get('restarts', 0):<10}"
            )

    def print_pods_by_namespace(self) -> None:
        """Print pod count by namespace."""
        print("\n📊 Pods by Namespace\n")

        organized = self.get_pods_by_namespace()

        if not organized:
            print("No pods found")
            return

        print(f"{'Namespace':<30} {'Pod Count':<10}")
        print("─" * 40)

        total = 0
        for ns in sorted(organized.keys()):
            count = len(organized[ns])
            total += count
            print(f"{ns:<30} {count:<10}")

        print("─" * 40)
        print(f"{'Total':<30} {total:<10}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Search and analyze Kubernetes resources"
    )
    parser.add_argument(
        "--search-pods",
        help="Search for pods by image pattern",
        metavar="PATTERN",
    )
    parser.add_argument(
        "--unhealthy",
        action="store_true",
        help="Show unhealthy pods",
    )
    parser.add_argument(
        "--high-restart",
        type=int,
        help="Show pods with restart count > N",
        metavar="N",
    )
    parser.add_argument(
        "--by-namespace",
        action="store_true",
        help="Show pods grouped by namespace",
    )
    parser.add_argument(
        "--export-json",
        help="Export cluster snapshot to JSON file",
        metavar="FILE",
    )

    args = parser.parse_args()

    try:
        searcher = ResourceSearcher()

        if not searcher.client.is_connected():
            print("❌ Failed to connect to MCP server")
            return 1

        # Default: show by namespace
        if not any([args.search_pods, args.unhealthy, args.high_restart, args.by_namespace, args.export_json]):
            searcher.print_pods_by_namespace()
        else:
            if args.search_pods:
                searcher.print_pods_by_image(args.search_pods)

            if args.unhealthy:
                searcher.print_unhealthy_pods()

            if args.high_restart is not None:
                searcher.print_high_restart_pods(args.high_restart)

            if args.by_namespace:
                searcher.print_pods_by_namespace()

            if args.export_json:
                searcher.export_cluster_snapshot(Path(args.export_json))

        return 0

    except KeyboardInterrupt:
        print("\n\nInterrupted")
        return 1
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        return 1
    finally:
        searcher.client.disconnect()


if __name__ == "__main__":
    sys.exit(main())
