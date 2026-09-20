"""
Polling implementation of IClusterWatcher.
"""
from typing import Any, Dict, List
from src.core.interfaces import IToolGateway
from src.daemon.interfaces import IClusterWatcher


class PollingClusterWatcher(IClusterWatcher):
    """
    Cluster anomaly watcher using periodic tool gateway queries.
    """

    def __init__(self, tool_gateway: IToolGateway):
        self._tool_gateway = tool_gateway

    def detect_anomalies(self, namespace: str) -> List[Dict[str, Any]]:
        """Queries the tool gateway for crashing or degraded pods."""
        res = self._tool_gateway.execute_tool("list_unhealthy_pods", {"namespace": namespace})
        if res.success and isinstance(res.output, list):
            return res.output
        return []
