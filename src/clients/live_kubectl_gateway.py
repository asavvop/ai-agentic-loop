"""
Live Kubernetes Tool Gateway executing real kubectl commands against a cluster.
"""
import inspect
import json
import logging
import subprocess
from typing import Any, Dict, List, Optional
from src.core.interfaces import IToolGateway, ToolResult

logger = logging.getLogger("LiveKubectlGateway")


class LiveKubectlGateway(IToolGateway):
    """
    Adapter executing live kubectl CLI operations against an active Kubernetes cluster (e.g. k3s).
    """

    def __init__(self, kubeconfig: Optional[str] = "/etc/rancher/k3s/k3s.yaml"):
        self._kubeconfig = kubeconfig
        self._registry = {
            "list_unhealthy_pods": self._list_unhealthy_pods,
            "get_pod_logs": self._get_pod_logs,
            "get_pod_events": self._get_pod_events,
            "get_deployment_status": self._get_deployment_status,
            "patch_deployment_resources": self._patch_deployment_resources,
            "restart_deployment": self._restart_deployment
        }

    def _run_kubectl(self, args: List[str]) -> str:
        cmd = ["kubectl"]
        if self._kubeconfig:
            cmd.extend(["--kubeconfig", self._kubeconfig])
        cmd.extend(args)
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return res.stdout.strip()

    def get_available_tools(self) -> List[str]:
        return list(self._registry.keys())

    def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> ToolResult:
        if tool_name not in self._registry:
            return ToolResult(
                success=False,
                output=None,
                error_message=f"Tool '{tool_name}' not supported in LiveKubectlGateway."
            )

        tool_fn = self._registry[tool_name]
        try:
            # Filter arguments to match the method signature
            sig = inspect.signature(tool_fn)
            filtered_args = {}
            for param_name in sig.parameters.keys():
                if param_name in arguments:
                    filtered_args[param_name] = arguments[param_name]

            output = tool_fn(**filtered_args)
            return ToolResult(success=True, output=output)
        except Exception as e:
            logger.error(f"Failed to execute live kubectl tool '{tool_name}': {e}")
            return ToolResult(success=False, output=None, error_message=str(e))

    def _list_unhealthy_pods(self, namespace: str) -> List[Dict[str, Any]]:
        raw_json = self._run_kubectl(["get", "pods", "-n", namespace, "-o", "json"])
        data = json.loads(raw_json)
        unhealthy = []

        for item in data.get("items", []):
            pod_name = item["metadata"]["name"]
            status_obj = item.get("status", {})
            phase = status_obj.get("phase", "Unknown")
            c_statuses = status_obj.get("containerStatuses", [])

            is_pod_unhealthy = phase != "Running"
            failure_reason = phase
            restart_count = 0
            last_reason = "Unknown"

            for c in c_statuses:
                restart_count += c.get("restartCount", 0)
                waiting = c.get("state", {}).get("waiting", {})
                terminated = c.get("lastState", {}).get("terminated", {})

                if waiting:
                    failure_reason = waiting.get("reason", "Waiting")
                    is_pod_unhealthy = True
                if terminated:
                    last_reason = terminated.get("reason", "Terminated")
                    if last_reason in ["OOMKilled", "Error"]:
                        is_pod_unhealthy = True

            if is_pod_unhealthy or restart_count > 0:
                workload_name = item["metadata"].get("labels", {}).get("app") or pod_name.split("-")[0]
                unhealthy.append({
                    "pod_name": pod_name,
                    "namespace": namespace,
                    "workload": workload_name,
                    "status": failure_reason,
                    "restart_count": restart_count,
                    "last_state": last_reason
                })

        return unhealthy

    def _get_pod_logs(self, namespace: str, pod_name: str) -> str:
        try:
            logs = self._run_kubectl(["logs", pod_name, "-n", namespace, "--tail=50"])
            if logs:
                return logs
        except Exception:
            pass

        try:
            return self._run_kubectl(["logs", pod_name, "-n", namespace, "--previous", "--tail=50"])
        except Exception as e:
            return f"Log retrieval error: {str(e)}"

    def _get_pod_events(self, namespace: str, pod_name: str) -> List[str]:
        raw_json = self._run_kubectl(["get", "events", "-n", namespace, "--field-selector", f"involvedObject.name={pod_name}", "-o", "json"])
        data = json.loads(raw_json)
        return [ev.get("message", "") for ev in data.get("items", [])]

    def _get_deployment_status(self, namespace: str, deployment_name: str) -> Dict[str, Any]:
        raw_json = self._run_kubectl(["get", "deployment", deployment_name, "-n", namespace, "-o", "json"])
        dep = json.loads(raw_json)
        spec_replicas = dep.get("spec", {}).get("replicas", 0)
        ready_replicas = dep.get("status", {}).get("readyReplicas", 0)

        status_str = "Healthy" if ready_replicas == spec_replicas and ready_replicas > 0 else "Degraded"
        return {
            "namespace": namespace,
            "deployment": deployment_name,
            "desiredReplicas": spec_replicas,
            "readyReplicas": ready_replicas,
            "status": status_str
        }

    def _patch_deployment_resources(self, namespace: str, deployment_name: str, memory_limit: str = "512Mi") -> Dict[str, Any]:
        self._run_kubectl(["set", "resources", f"deployment/{deployment_name}", "-n", namespace, f"--limits=memory={memory_limit}"])
        # Wait for Kubernetes rolling update to complete so new pods become Ready
        try:
            self._run_kubectl(["rollout", "status", f"deployment/{deployment_name}", "-n", namespace, "--timeout=25s"])
        except Exception as e:
            logger.warning(f"Rollout status wait timed out: {e}")

        return {
            "status": "Patched",
            "deployment": deployment_name,
            "new_memory_limit": memory_limit
        }

    def _restart_deployment(self, namespace: str, deployment_name: str) -> Dict[str, Any]:
        self._run_kubectl(["rollout", "restart", f"deployment/{deployment_name}", "-n", namespace])
        try:
            self._run_kubectl(["rollout", "status", f"deployment/{deployment_name}", "-n", namespace, "--timeout=25s"])
        except Exception as e:
            logger.warning(f"Rollout status wait timed out: {e}")
        return {"status": "RestartTriggered", "deployment": deployment_name}
