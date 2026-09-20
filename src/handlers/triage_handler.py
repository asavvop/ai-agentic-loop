"""
Triage State Handler for Kubernetes Workload Assessment.
"""
from typing import Any, Dict, List, Optional
from src.core.context import AgentContext, AgentState
from src.core.interfaces import ToolResult
from src.handlers.base_handler import BaseStateHandler


class TriageStateHandler(BaseStateHandler):
    """
    Initial state handler: audits namespace for failing, crashing, or OOM pods.
    """

    @property
    def state(self) -> AgentState:
        return AgentState.TRIAGE

    @property
    def allowed_tools(self) -> List[str]:
        return ["list_unhealthy_pods", "get_deployment_status"]

    def build_system_prompt(self, context: AgentContext) -> str:
        return (
            "You are a Kubernetes SRE Triage Agent.\n"
            f"Your objective: Inspect the target namespace ('{context.target_namespace}') and identify crashing, OOMKilled, or degraded pods.\n"
            "Action Rules:\n"
            "1. You MUST call 'list_unhealthy_pods' with action_args: {\"namespace\": \"" + context.target_namespace + "\"}.\n"
            "2. If unhealthy pods are discovered, set has_unhealthy_workloads=True."
        )

    def get_response_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "reasoning": {"type": "string", "description": "Analysis of current state"},
                "action": {"type": "string", "enum": ["list_unhealthy_pods", "get_deployment_status", "none"]},
                "action_args": {
                    "type": "object",
                    "properties": {
                        "namespace": {"type": "string", "description": "Target Kubernetes namespace"}
                    },
                    "required": ["namespace"]
                },
                "has_unhealthy_workloads": {"type": "boolean"},
                "target_workload": {"type": "string"}
            },
            "required": ["reasoning", "action", "action_args", "has_unhealthy_workloads"]
        }

    def evaluate_transition(
        self,
        context: AgentContext,
        decision: Dict[str, Any],
        action_output: Optional[ToolResult]
    ) -> AgentState:
        # If tool returned unhealthy pods, populate blackboard
        if action_output and action_output.success and action_output.output is not None:
            unhealthy_pods = action_output.output
            if isinstance(unhealthy_pods, list):
                if len(unhealthy_pods) > 0:
                    context.blackboard["unhealthy_pods"] = unhealthy_pods
                    if not context.target_workload:
                        context.target_workload = unhealthy_pods[0].get("workload") or unhealthy_pods[0].get("pod_name")
                    return AgentState.INVESTIGATE
                else:
                    return AgentState.RESOLVED

        if decision.get("has_unhealthy_workloads") or context.blackboard.get("unhealthy_pods"):
            return AgentState.INVESTIGATE

        # If tool errored and we have budget, retry
        if context.state_step_count < context.max_steps_per_state:
            return AgentState.TRIAGE

        return AgentState.FAILED
