"""
MCP Server exposing Kubernetes Diagnostics and Self-Healing Tools with OpenTelemetry.
"""
import json
from typing import Any, Dict, List, Optional
from opentelemetry import trace
try:
    from mcp.server.fastmcp import FastMCP
except (ImportError, ModuleNotFoundError):
    try:
        from mcp.server.mcpserver import MCPServer as FastMCP
    except (ImportError, ModuleNotFoundError):
        class FastMCP:  # type: ignore
            def __init__(self, name: str):
                self.name = name
            def tool(self):
                def decorator(fn):
                    return fn
                return decorator
            def run(self, transport: str = "stdio"):
                pass

from src.server.k8s_telemetry import K8sClusterTelemetry

tracer = trace.get_tracer("agentic.mcp.k8s_tools")
telemetry = K8sClusterTelemetry()
mcp = FastMCP("EnterpriseK8sDiagnosticTools")


def _is_authorized_namespace(namespace: str) -> bool:
    return namespace.lower().strip() in ["production", "staging"]


@mcp.tool()
def list_unhealthy_pods(namespace: str) -> str:
    """Lists crashing, OOMKilled, or degraded pods in a Kubernetes namespace."""
    with tracer.start_as_current_span("mcp.tool.list_unhealthy_pods") as span:
        span.set_attribute("k8s.namespace", namespace)
        if not _is_authorized_namespace(namespace):
            return json.dumps({"error": "Unauthorized namespace policy violation"})
        return json.dumps(telemetry.list_unhealthy_pods(namespace))


@mcp.tool()
def get_pod_logs(namespace: str, pod_name: str) -> str:
    """Fetches the most recent log buffer and error traces for a given pod."""
    with tracer.start_as_current_span("mcp.tool.get_pod_logs") as span:
        span.set_attribute("k8s.namespace", namespace)
        span.set_attribute("k8s.pod_name", pod_name)
        if not _is_authorized_namespace(namespace):
            return json.dumps({"error": "Unauthorized namespace policy violation"})
        return telemetry.get_pod_logs(namespace, pod_name)


@mcp.tool()
def get_pod_events(namespace: str, pod_name: str) -> str:
    """Fetches Kubernetes lifecycle events and back-off messages for a pod."""
    with tracer.start_as_current_span("mcp.tool.get_pod_events") as span:
        span.set_attribute("k8s.namespace", namespace)
        span.set_attribute("k8s.pod_name", pod_name)
        if not _is_authorized_namespace(namespace):
            return json.dumps({"error": "Unauthorized namespace policy violation"})
        return json.dumps(telemetry.get_pod_events(namespace, pod_name))


@mcp.tool()
def get_deployment_status(namespace: str, deployment_name: str) -> str:
    """Queries health, replica readiness, and resource limits of a deployment."""
    with tracer.start_as_current_span("mcp.tool.get_deployment_status") as span:
        span.set_attribute("k8s.namespace", namespace)
        span.set_attribute("k8s.deployment", deployment_name)
        if not _is_authorized_namespace(namespace):
            return json.dumps({"error": "Unauthorized namespace policy violation"})
        return json.dumps(telemetry.get_deployment_status(namespace, deployment_name))


@mcp.tool()
def patch_deployment_resources(namespace: str, deployment_name: str, memory_limit: str) -> str:
    """Gated remediation tool: Patches container memory limits for a crashing deployment."""
    with tracer.start_as_current_span("mcp.tool.patch_deployment_resources") as span:
        span.set_attribute("k8s.namespace", namespace)
        span.set_attribute("k8s.deployment", deployment_name)
        span.set_attribute("k8s.patch.memory_limit", memory_limit)
        if not _is_authorized_namespace(namespace):
            return json.dumps({"error": "Unauthorized namespace policy violation"})
        return json.dumps(telemetry.patch_deployment_resources(namespace, deployment_name, memory_limit))


@mcp.tool()
def restart_deployment(namespace: str, deployment_name: str) -> str:
    """Gated remediation tool: Triggers a rolling restart for a deployment."""
    with tracer.start_as_current_span("mcp.tool.restart_deployment") as span:
        span.set_attribute("k8s.namespace", namespace)
        span.set_attribute("k8s.deployment", deployment_name)
        if not _is_authorized_namespace(namespace):
            return json.dumps({"error": "Unauthorized namespace policy violation"})
        return json.dumps(telemetry.restart_deployment(namespace, deployment_name))


if __name__ == "__main__":
    mcp.run(transport="stdio")
