"""
Core interfaces for Dependency Inversion and decoupling.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class ToolResult:
    """Standardized envelope for tool execution results."""
    success: bool
    output: Any
    error_message: Optional[str] = None

    def to_summary(self) -> str:
        """Returns a string representation of the output or error."""
        if self.success:
            return str(self.output)
        return f"Tool Error: {self.error_message}"


class ILLMClient(ABC):
    """Abstract interface for structured LLM inference."""

    @abstractmethod
    def generate_structured_decision(
        self,
        system_prompt: str,
        user_prompt: str,
        response_schema: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generates a validated structured JSON decision dictionary."""
        pass


class IToolGateway(ABC):
    """Abstract interface for discovering and invoking tools."""

    @abstractmethod
    def get_available_tools(self) -> List[str]:
        """Returns a list of tool names exposed by the gateway."""
        pass

    @abstractmethod
    def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> ToolResult:
        """Executes a tool with the provided arguments safely."""
        pass
