"""
Verification State Handler for Post-Remediation Health Validation.
"""
from typing import Any, Dict, List, Optional
from src.core.context import AgentContext, AgentState
from src.core.interfaces import ToolResult
from src.handlers.base_handler import BaseStateHandler


class VerifyStateHandler(BaseStateHandler):
    """
    Verification handler: queries post-remediation health telemetry to confirm resolution.
    """

    @property
    def state(self) -> AgentState:
        return AgentState.VERIFY

    @property
    def allowed_tools(self) -> List[str]:
        return ["get_deployment_status", "list_unhealthy_pods"]

    def build_system_prompt(self, context: AgentContext) -> str:
        workload = context.target_workload or "payment-service"
        return (
            "You are a Kubernetes SRE Verification Specialist.\n"
            f"Workload to verify: {workload} in namespace '{context.target_namespace}'\n"
            "Action Rules:\n"
            f"1. Query deployment health by calling 'get_deployment_status' with action_args: {{\"namespace\": \"{context.target_namespace}\", \"deployment_name\": \"{workload}\"}}.\n"
            "2. If readyReplicas == desiredReplicas and status == 'Healthy', set is_fully_healthy=True."
        )

    def get_response_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "reasoning": {"type": "string"},
                "action": {"type": "string", "enum": ["get_deployment_status", "list_unhealthy_pods"]},
                "action_args": {
                    "type": "object",
                    "properties": {
                        "namespace": {"type": "string"},
                        "deployment_name": {"type": "string"}
                    },
                    "required": ["namespace", "deployment_name"]
                },
                "is_fully_healthy": {"type": "boolean"}
            },
            "required": ["reasoning", "action", "action_args", "is_fully_healthy"]
        }

    def evaluate_transition(
        self,
        context: AgentContext,
        decision: Dict[str, Any],
        action_output: Optional[ToolResult]
    ) -> AgentState:
        if action_output and action_output.success and action_output.output:
            status = action_output.output
            if isinstance(status, dict):
                ready = status.get("readyReplicas", 0)
                desired = status.get("desiredReplicas", 0)
                health_status = status.get("status", "")
                if ready == desired and health_status == "Healthy" and desired > 0:
                    context.blackboard["final_verification"] = status
                    return AgentState.RESOLVED

        if decision.get("is_fully_healthy"):
            return AgentState.RESOLVED

        # If not healthy and budget remains, retry investigation
        if context.step_count < 10:
            return AgentState.INVESTIGATE

        return AgentState.FAILED
