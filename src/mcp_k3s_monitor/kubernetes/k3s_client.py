"""
K3sClient - High-level wrapper for Kubernetes cluster operations.

Provides a simple, intuitive interface for common k3s cluster queries including:
- Cluster health and status
- Pod listing and log retrieval
- Deployments, services, and nodes
- Namespace management
"""

import os
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import logging

from kubernetes import client, config, watch
from kubernetes.client.rest import ApiException


logger = logging.getLogger(__name__)


@dataclass
class PodInfo:
    """Pod information data class"""
    name: str
    namespace: str
    status: str
    ready: str
    restarts: int
    age: str
    ip: Optional[str] = None
    node: Optional[str] = None
    image: Optional[str] = None
    cpu: Optional[str] = None
    memory: Optional[str] = None


@dataclass
class ClusterHealth:
    """Cluster health information"""
    status: str
    nodes_count: int
    nodes_ready: int
    nodes_not_ready: int
    pods_count: int
    pods_running: int
    pods_pending: int
    pods_failed: int
    services_count: int
    deployments_count: int


@dataclass
class DeploymentInfo:
    """Deployment information"""
    name: str
    namespace: str
    ready_replicas: int
    desired_replicas: int
    updated_replicas: int
    available_replicas: int
    image: Optional[str] = None
    age: Optional[str] = None


class K3sClientError(Exception):
    """Base exception for K3sClient"""
    pass


class K3sClient:
    """
    High-level client for k3s cluster operations.

    Handles kubeconfig loading, cluster connections, and common queries.
    """

    def __init__(self, kubeconfig_path: Optional[str] = None):
        """
        Initialize K3sClient with kubeconfig.

        Args:
            kubeconfig_path: Path to kubeconfig file.
                           Defaults to ~/.kube/config if not provided.

        Raises:
            K3sClientError: If kubeconfig cannot be loaded or cluster is unreachable.
        """
        self.kubeconfig_path = kubeconfig_path or os.getenv(
            'KUBECONFIG',
            str(Path.home() / '.kube' / 'config')
        )

        try:
            config.load_kube_config(self.kubeconfig_path)
            self.v1 = client.CoreV1Api()
            self.apps_v1 = client.AppsV1Api()
            self.batch_v1 = client.BatchV1Api()
            logger.info(f"Connected to Kubernetes cluster using {self.kubeconfig_path}")
        except Exception as e:
            raise K3sClientError(f"Failed to load kubeconfig: {e}")

    def get_cluster_health(self) -> ClusterHealth:
        """
        Get overall cluster health status.

        Returns:
            ClusterHealth object with cluster statistics.
        """
        try:
            # Get nodes
            nodes = self.v1.list_node()
            nodes_ready = sum(
                1 for node in nodes.items
                if any(
                    condition.status == "True" and condition.type == "Ready"
                    for condition in node.status.conditions
                )
            )

            # Get pods
            pods = self.v1.list_pod_for_all_namespaces()
            pods_running = sum(1 for pod in pods.items if pod.status.phase == "Running")
            pods_pending = sum(1 for pod in pods.items if pod.status.phase == "Pending")
            pods_failed = sum(1 for pod in pods.items if pod.status.phase == "Failed")

            # Get services
            services = self.v1.list_service_for_all_namespaces()

            # Get deployments
            deployments = self.apps_v1.list_deployment_for_all_namespaces()

            return ClusterHealth(
                status="healthy" if nodes_ready == len(nodes.items) else "degraded",
                nodes_count=len(nodes.items),
                nodes_ready=nodes_ready,
                nodes_not_ready=len(nodes.items) - nodes_ready,
                pods_count=len(pods.items),
                pods_running=pods_running,
                pods_pending=pods_pending,
                pods_failed=pods_failed,
                services_count=len(services.items),
                deployments_count=len(deployments.items),
            )
        except ApiException as e:
            raise K3sClientError(f"API error getting cluster health: {e}")

    def list_pods(
        self,
        namespace: Optional[str] = None,
        label_selector: Optional[str] = None,
        field_selector: Optional[str] = None,
    ) -> List[PodInfo]:
        """
        List pods with filtering options.

        Args:
            namespace: Specific namespace to query. If None, queries all namespaces.
            label_selector: Label selector for filtering (e.g., "app=myapp").
            field_selector: Field selector for filtering (e.g., "status.phase=Running").

        Returns:
            List of PodInfo objects.
        """
        try:
            if namespace:
                pods = self.v1.list_namespaced_pod(
                    namespace,
                    label_selector=label_selector,
                    field_selector=field_selector,
                )
            else:
                pods = self.v1.list_pod_for_all_namespaces(
                    label_selector=label_selector,
                    field_selector=field_selector,
                )

            result = []
            for pod in pods.items:
                # Calculate ready containers
                ready = 0
                if pod.status.container_statuses:
                    ready = sum(1 for cs in pod.status.container_statuses if cs.ready)
                total = len(pod.spec.containers) if pod.spec.containers else 0

                # Get image
                image = None
                if pod.spec.containers:
                    image = pod.spec.containers[0].image

                # Calculate restarts
                restarts = 0
                if pod.status.container_statuses:
                    restarts = sum(cs.restart_count or 0 for cs in pod.status.container_statuses)

                # Calculate age
                created = pod.metadata.creation_timestamp or datetime.now()
                age = self._format_age(created)

                pod_info = PodInfo(
                    name=pod.metadata.name,
                    namespace=pod.metadata.namespace,
                    status=pod.status.phase,
                    ready=f"{ready}/{total}",
                    restarts=restarts,
                    age=age,
                    ip=pod.status.pod_ip,
                    node=pod.spec.node_name,
                    image=image,
                )
                result.append(pod_info)

            return result
        except ApiException as e:
            raise K3sClientError(f"API error listing pods: {e}")

    def get_pod_logs(
        self,
        pod_name: str,
        namespace: str,
        container: Optional[str] = None,
        lines: int = 50,
        follow: bool = False,
    ) -> str:
        """
        Get logs from a pod.

        Args:
            pod_name: Name of the pod.
            namespace: Namespace containing the pod.
            container: Specific container name. If None, uses first container.
            lines: Number of log lines to retrieve.
            follow: If True, stream logs (limited to iterator).

        Returns:
            Pod logs as string.
        """
        try:
            logs = self.v1.read_namespaced_pod_log(
                pod_name,
                namespace,
                container=container,
                tail_lines=lines,
            )
            return logs
        except ApiException as e:
            raise K3sClientError(f"API error getting pod logs: {e}")

    def list_deployments(
        self,
        namespace: Optional[str] = None,
    ) -> List[DeploymentInfo]:
        """
        List deployments.

        Args:
            namespace: Specific namespace to query. If None, queries all namespaces.

        Returns:
            List of DeploymentInfo objects.
        """
        try:
            if namespace:
                deployments = self.apps_v1.list_namespaced_deployment(namespace)
            else:
                deployments = self.apps_v1.list_deployment_for_all_namespaces()

            result = []
            for deploy in deployments.items:
                # Get image from first container
                image = None
                if deploy.spec.template.spec.containers:
                    image = deploy.spec.template.spec.containers[0].image

                # Calculate age
                created = deploy.metadata.creation_timestamp or datetime.now()
                age = self._format_age(created)

                deploy_info = DeploymentInfo(
                    name=deploy.metadata.name,
                    namespace=deploy.metadata.namespace,
                    ready_replicas=deploy.status.ready_replicas or 0,
                    desired_replicas=deploy.spec.replicas or 0,
                    updated_replicas=deploy.status.updated_replicas or 0,
                    available_replicas=deploy.status.available_replicas or 0,
                    image=image,
                    age=age,
                )
                result.append(deploy_info)

            return result
        except ApiException as e:
            raise K3sClientError(f"API error listing deployments: {e}")

    def list_services(
        self,
        namespace: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        List services.

        Args:
            namespace: Specific namespace to query. If None, queries all namespaces.

        Returns:
            List of service information dictionaries.
        """
        try:
            if namespace:
                services = self.v1.list_namespaced_service(namespace)
            else:
                services = self.v1.list_service_for_all_namespaces()

            result = []
            for svc in services.items:
                # Get cluster IP and external IP
                cluster_ip = svc.spec.cluster_ip
                external_ip = "None"
                if svc.status.load_balancer.ingress:
                    external_ip = svc.status.load_balancer.ingress[0].ip or "Pending"

                # Get ports
                ports = []
                if svc.spec.ports:
                    for port in svc.spec.ports:
                        ports.append({
                            "name": port.name,
                            "protocol": port.protocol,
                            "port": port.port,
                            "target_port": port.target_port,
                        })

                service_info = {
                    "name": svc.metadata.name,
                    "namespace": svc.metadata.namespace,
                    "type": svc.spec.type,
                    "cluster_ip": cluster_ip,
                    "external_ip": external_ip,
                    "ports": ports,
                }
                result.append(service_info)

            return result
        except ApiException as e:
            raise K3sClientError(f"API error listing services: {e}")

    def list_nodes(self) -> List[Dict[str, Any]]:
        """
        List cluster nodes.

        Returns:
            List of node information dictionaries.
        """
        try:
            nodes = self.v1.list_node()

            result = []
            for node in nodes.items:
                # Get status conditions
                ready_status = "Unknown"
                if node.status.conditions:
                    for condition in node.status.conditions:
                        if condition.type == "Ready":
                            ready_status = condition.status

                # Get allocatable resources
                allocatable = node.status.allocatable or {}

                # Get addresses
                address = "Unknown"
                if node.status.addresses:
                    for addr in node.status.addresses:
                        if addr.type == "InternalIP":
                            address = addr.address

                node_info = {
                    "name": node.metadata.name,
                    "status": ready_status,
                    "roles": node.metadata.labels.get("node-role.kubernetes.io/control-plane", "worker"),
                    "address": address,
                    "kubelet_version": node.status.node_info.kubelet_version,
                    "cpu": allocatable.get("cpu", "Unknown"),
                    "memory": allocatable.get("memory", "Unknown"),
                }
                result.append(node_info)

            return result
        except ApiException as e:
            raise K3sClientError(f"API error listing nodes: {e}")

    def list_namespaces(self) -> List[str]:
        """
        List all namespaces.

        Returns:
            List of namespace names.
        """
        try:
            namespaces = self.v1.list_namespace()
            return [ns.metadata.name for ns in namespaces.items]
        except ApiException as e:
            raise K3sClientError(f"API error listing namespaces: {e}")

    def get_resource_usage(self, namespace: Optional[str] = None) -> Dict[str, Any]:
        """
        Get approximate resource usage (requires metrics-server).

        Note: This requires the metrics-server to be installed in the cluster.

        Args:
            namespace: Specific namespace to query. If None, queries all namespaces.

        Returns:
            Dictionary with resource usage information.
        """
        try:
            # Try to get pod metrics
            from kubernetes import client as metrics_client

            if namespace:
                pods = self.v1.list_namespaced_pod(namespace)
            else:
                pods = self.v1.list_pod_for_all_namespaces()

            total_cpu = 0
            total_memory = 0
            pod_count = len(pods.items)

            # Calculate approximate usage from requests
            for pod in pods.items:
                if pod.spec.containers:
                    for container in pod.spec.containers:
                        if container.resources and container.resources.requests:
                            cpu_str = container.resources.requests.get("cpu", "0")
                            mem_str = container.resources.requests.get("memory", "0")

                            # Simple parsing (m = millicores, Mi = mebibytes)
                            if cpu_str.endswith("m"):
                                total_cpu += int(cpu_str[:-1])
                            elif cpu_str:
                                total_cpu += int(float(cpu_str) * 1000)

                            if mem_str.endswith("Mi"):
                                total_memory += int(mem_str[:-2])

            return {
                "total_pods": pod_count,
                "total_cpu_millicores": total_cpu,
                "total_memory_mi": total_memory,
                "note": "Based on resource requests, not actual usage",
            }
        except Exception as e:
            logger.warning(f"Could not get resource metrics: {e}")
            return {
                "error": str(e),
                "note": "Metrics server may not be installed",
            }

    def _format_age(self, created: datetime) -> str:
        """Format creation timestamp as human-readable age."""
        now = datetime.now(created.tzinfo) if created.tzinfo else datetime.now()
        delta = now - created

        seconds = int(delta.total_seconds())
        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            return f"{seconds // 60}m"
        elif seconds < 86400:
            return f"{seconds // 3600}h"
        else:
            return f"{seconds // 86400}d"
