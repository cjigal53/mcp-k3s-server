#!/usr/bin/env python3
"""
MCP k3s Monitoring Server - Main Entry Point

A Model Context Protocol (MCP) server that enables chatbots to query and monitor Kubernetes (k3s) clusters. The server provides tools for checking cluster health, pod status, resource usage, logs, and other cluster information via a standardized MCP interface.
"""

import argparse
import sys
from pathlib import Path


def main():
    """Main entry point for MCP k3s Monitoring Server"""
    parser = argparse.ArgumentParser(
        description="A Model Context Protocol (MCP) server that enables chatbots to query and monitor Kubernetes (k3s) clusters. The server provides tools for checking cluster health, pod status, resource usage, logs, and other cluster information via a standardized MCP interface."
    )
    parser.add_argument(
        "--version",
        action="version",
        version="0.1.0"
    )

    args = parser.parse_args()

    print("MCP k3s Monitoring Server is running!")
    # Add your application logic here


if __name__ == "__main__":
    sys.exit(main())
