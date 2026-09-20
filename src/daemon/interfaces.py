"""
Abstract interfaces for the Daemon subsystem enforcing DIP and ISP.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List
from src.core.context import AgentContext


class IClusterWatcher(ABC):
    """Abstract interface for detecting cluster anomalies and triggers."""

    @abstractmethod
    def detect_anomalies(self, namespace: str) -> List[Dict[str, Any]]:
        """Returns a list of detected unhealthy pods or anomalies in the namespace."""
        pass


class IDaemonObserver(ABC):
    """Abstract observer interface for metrics, logging, and notifications."""

    @abstractmethod
    def on_cycle_start(self, namespace: str) -> None:
        pass

    @abstractmethod
    def on_self_healing_triggered(self, namespace: str, anomalies: List[Dict[str, Any]]) -> None:
        pass

    @abstractmethod
    def on_self_healing_completed(self, final_context: AgentContext) -> None:
        pass
