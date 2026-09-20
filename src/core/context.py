"""
Context and State representations for the FSM Agentic Loop.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class AgentState(Enum):
    """Enumeration of possible discrete states in the diagnostic & healing FSM."""
    TRIAGE = "TRIAGE"
    INVESTIGATE = "INVESTIGATE"
    REMEDIATE = "REMEDIATE"
    VERIFY = "VERIFY"
    RESOLVED = "RESOLVED"
    FAILED = "FAILED"

    @property
    def is_terminal(self) -> bool:
        """Returns True if the state is a final/stopping state."""
        return self in (AgentState.RESOLVED, AgentState.FAILED)


@dataclass
class AgentContext:
    """
    Shared blackboard containing working memory, diagnostic artifacts,
    turn budgets, and full execution audit history.
    """
    target_namespace: str
    target_workload: Optional[str] = None
    state: AgentState = AgentState.TRIAGE
    step_count: int = 0
    state_step_count: int = 0
    max_steps_per_state: int = 4
    blackboard: Dict[str, Any] = field(default_factory=dict)
    execution_history: List[Dict[str, Any]] = field(default_factory=list)

    def transition_to(self, next_state: AgentState) -> None:
        """Transitions to next state and resets state step counter."""
        if next_state != self.state:
            self.state = next_state
            self.state_step_count = 0

    def increment_turn(self) -> None:
        """Increments both global and state turn counters."""
        self.step_count += 1
        self.state_step_count += 1

    def record_step(
        self,
        from_state: AgentState,
        to_state: AgentState,
        decision: Dict[str, Any],
        action_output: Any = None
    ) -> None:
        """Appends an immutable record of the executed turn to history."""
        self.execution_history.append({
            "step": self.step_count,
            "state_step": self.state_step_count,
            "from_state": from_state.name,
            "to_state": to_state.name,
            "decision": decision,
            "action_output": action_output
        })
