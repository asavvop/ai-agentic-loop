"""
Remediation State Handler for Gated Autonomous Self-Healing Actions.
"""
from typing import Any, Dict, List, Optional
from src.core.context import AgentContext, AgentState
from src.core.interfaces import ToolResult
from src.handlers.base_handler import BaseStateHandler


class RemediationStateHandler(BaseStateHandler):
    """
    Remediation handler: safely applies fixes (resource patching, rollout restart)
    based on diagnostic findings from the INVESTIGATE phase.
    """

    @property
    def state(self) -> AgentState:
        return AgentState.REMEDIATE

    @property
    def allowed_tools(self) -> List[str]:
        return ["patch_deployment_resources", "restart_deployment"]

    def build_system_prompt(self, context: AgentContext) -> str:
        rec_action = context.blackboard.get("recommended_action", "patch_memory")
        workload = context.target_workload or "payment-service"
        return (
            "You are a Kubernetes SRE Self-Healing Engine.\n"
            f"Diagnosis: {context.blackboard.get('root_cause', 'Unknown')}\n"
            f"Recommended Strategy: {rec_action}\n"
            f"Target Workload: {workload}\n"
            "Action Rules:\n"
            f"1. Call 'patch_deployment_resources' with action_args: {{\"namespace\": \"{context.target_namespace}\", \"deployment_name\": \"{workload}\", \"memory_limit\": \"2Gi\"}}.\n"
            "2. Set remediation_initiated=True."
        )

    def get_response_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "reasoning": {"type": "string"},
                "action": {"type": "string", "enum": ["patch_deployment_resources", "restart_deployment"]},
                "action_args": {
                    "type": "object",
                    "properties": {
                        "namespace": {"type": "string"},
                        "deployment_name": {"type": "string"},
                        "memory_limit": {"type": "string"}
                    },
                    "required": ["namespace", "deployment_name"]
                },
                "remediation_initiated": {"type": "boolean"}
            },
            "required": ["reasoning", "action", "action_args", "remediation_initiated"]
        }

    def evaluate_transition(
        self,
        context: AgentContext,
        decision: Dict[str, Any],
        action_output: Optional[ToolResult]
    ) -> AgentState:
        if action_output and action_output.success:
            context.blackboard["remediation_result"] = action_output.output
            return AgentState.VERIFY

        if decision.get("remediation_initiated"):
            return AgentState.VERIFY

        return AgentState.FAILED
