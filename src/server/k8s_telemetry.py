"""
Cluster Telemetry State and Simulation Model.
"""
from typing import Any, Dict, List


class K8sClusterTelemetry:
    """
    In-memory simulated telemetry repository representing cluster workloads and health.
    """

    def __init__(self):
        self.deployments: Dict[str, Dict[str, Any]] = {
            "payment-service": {
                "namespace": "production",
                "desiredReplicas": 3,
                "readyReplicas": 0,
                "status": "Degraded",
                "memory_limit": "512Mi"
            }
        }
        self.pods: List[Dict[str, Any]] = [
            {
                "pod_name": "payment-service-8f2a",
                "namespace": "production",
                "workload": "payment-service",
                "status": "CrashLoopBackOff",
                "restart_count": 5,
                "last_state": "OOMKilled"
            }
        ]
        self.logs: Dict[str, str] = {
            "payment-service-8f2a": (
                "[2026-09-20 16:45:10] INFO  Starting Payment Gateway Service...\n"
                "[2026-09-20 16:45:12] INFO  Initializing transaction buffers (pool_size=10000)...\n"
                "[2026-09-20 16:45:15] ERROR Exception in thread 'main' java.lang.OutOfMemoryError: Java heap space\n"
                "\tat com.enterprise.payment.BufferPool.allocate(BufferPool.java:142)\n"
                "[2026-09-20 16:45:15] FATAL Container terminated: exit code 137 (OOMKilled)"
            )
        }
        self.events: Dict[str, List[str]] = {
            "payment-service-8f2a": [
                "Back-off restarting failed container payment-gateway in pod payment-service-8f2a",
                "Container failed: OOMKilled"
            ]
        }

    def list_unhealthy_pods(self, namespace: str) -> List[Dict[str, Any]]:
        return [p for p in self.pods if p["namespace"] == namespace and p["status"] != "Running"]

    def get_pod_logs(self, namespace: str, pod_name: str) -> str:
        return self.logs.get(pod_name, "No logs available for pod.")

    def get_pod_events(self, namespace: str, pod_name: str) -> List[str]:
        return self.events.get(pod_name, ["No recent events found."])

    def get_deployment_status(self, namespace: str, deployment_name: str) -> Dict[str, Any]:
        dep = self.deployments.get(deployment_name)
        if not dep or dep["namespace"] != namespace:
            return {"error": f"Deployment '{deployment_name}' not found in namespace '{namespace}'."}
        return {
            "namespace": namespace,
            "deployment": deployment_name,
            "desiredReplicas": dep["desiredReplicas"],
            "readyReplicas": dep["readyReplicas"],
            "status": dep["status"],
            "memory_limit": dep["memory_limit"]
        }

    def patch_deployment_resources(self, namespace: str, deployment_name: str, memory_limit: str) -> Dict[str, Any]:
        if deployment_name in self.deployments and self.deployments[deployment_name]["namespace"] == namespace:
            dep = self.deployments[deployment_name]
            dep["memory_limit"] = memory_limit
            # Remediation fixes the crash: pod recovers and replicas match
            dep["readyReplicas"] = dep["desiredReplicas"]
            dep["status"] = "Healthy"
            self.pods = []  # No more crashing pods
            return {"status": "Patched", "deployment": deployment_name, "new_memory_limit": memory_limit}
        return {"error": "Deployment not found"}

    def restart_deployment(self, namespace: str, deployment_name: str) -> Dict[str, Any]:
        if deployment_name in self.deployments:
            return {"status": "RestartTriggered", "deployment": deployment_name}
        return {"error": "Deployment not found"}
