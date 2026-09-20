"""
MCP Gateway Adapter implementing IToolGateway.
"""
import inspect
import json
import logging
from typing import Any, Dict, List
from src.core.interfaces import IToolGateway, ToolResult
import src.server.mcp_k8s_server as server_module

logger = logging.getLogger("MCPGateway")


class DirectMCPToolGateway(IToolGateway):
    """
    In-process MCP Gateway executing FastMCP tools directly with parameter-filtering adapters.
    """

    def __init__(self):
        self._registry = {
            "list_unhealthy_pods": server_module.list_unhealthy_pods,
            "get_pod_logs": server_module.get_pod_logs,
            "get_pod_events": server_module.get_pod_events,
            "get_deployment_status": server_module.get_deployment_status,
            "patch_deployment_resources": server_module.patch_deployment_resources,
            "restart_deployment": server_module.restart_deployment
        }

    def get_available_tools(self) -> List[str]:
        return list(self._registry.keys())

    def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> ToolResult:
        if tool_name not in self._registry:
            return ToolResult(
                success=False,
                output=None,
                error_message=f"Tool '{tool_name}' is not registered in MCP gateway."
            )

        tool_fn = self._registry[tool_name]
        underlying_fn = getattr(tool_fn, "fn", tool_fn)

        try:
            # Filter arguments to match the tool signature exactly
            sig = inspect.signature(underlying_fn)
            filtered_args = {}
            for param_name in sig.parameters.keys():
                if param_name in arguments:
                    filtered_args[param_name] = arguments[param_name]

            raw_output = tool_fn(**filtered_args)
            try:
                parsed_output = json.loads(raw_output)
            except (ValueError, TypeError):
                parsed_output = raw_output
            return ToolResult(success=True, output=parsed_output)
        except Exception as e:
            logger.error(f"Error executing tool '{tool_name}': {e}")
            return ToolResult(success=False, output=None, error_message=str(e))
