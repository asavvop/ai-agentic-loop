"""
Abstract Base State Handler enforcing Liskov Substitution (LSP) and Open/Closed (OCP).
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from src.core.context import AgentContext, AgentState
from src.core.interfaces import ToolResult


class BaseStateHandler(ABC):
    """
    Abstract contract for an FSM State Handler.
    Each handler is responsible for prompt generation, response schema definition,
    tool scoping, and deterministic state transition evaluation for a single state.
    """

    @property
    @abstractmethod
    def state(self) -> AgentState:
        """The discrete AgentState managed by this handler."""
        pass

    @property
    @abstractmethod
    def allowed_tools(self) -> List[str]:
        """List of tool names permitted to be called in this state."""
        pass

    @abstractmethod
    def build_system_prompt(self, context: AgentContext) -> str:
        """Constructs the state-specific system prompt instruction."""
        pass

    @abstractmethod
    def get_response_schema(self) -> Dict[str, Any]:
        """Defines the strict JSON schema required for LLM output."""
        pass

    @abstractmethod
    def evaluate_transition(
        self,
        context: AgentContext,
        decision: Dict[str, Any],
        action_output: Optional[ToolResult]
    ) -> AgentState:
        """
        Evaluates the transition logic to determine the next AgentState.
        Combines model output with deterministic Python guardrails.
        """
        pass

    def build_user_prompt(self, context: AgentContext) -> str:
        """Default format for passing blackboard state and target context."""
        import json
        blackboard_snapshot = json.dumps(context.blackboard, indent=2) if context.blackboard else "{}"
        return (
            f"Target Namespace: {context.target_namespace}\n"
            f"Target Workload: {context.target_workload or 'Auto-Detect'}\n"
            f"Current State: {self.state.name} (Step {context.state_step_count + 1}/{context.max_steps_per_state})\n"
            f"Context Blackboard:\n{blackboard_snapshot}\n\n"
            "Analyze the telemetry and decide the next action or finding."
        )
