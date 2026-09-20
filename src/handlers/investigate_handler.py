"""
Investigation State Handler for Kubernetes Log Diagnostics and Root-Cause Isolation.
"""
from typing import Any, Dict, List, Optional
from src.core.context import AgentContext, AgentState
from src.core.interfaces import ToolResult
from src.handlers.base_handler import BaseStateHandler


class InvestigateStateHandler(BaseStateHandler):
    """
    Diagnostic handler: fetches logs, inspects stack traces, and isolates root cause.
    """

    @property
    def state(self) -> AgentState:
        return AgentState.INVESTIGATE

    @property
    def allowed_tools(self) -> List[str]:
        return ["get_pod_logs", "get_pod_events"]

    def build_system_prompt(self, context: AgentContext) -> str:
        failing_pod = "failing pod"
        pods = context.blackboard.get("unhealthy_pods", [])
        if pods and isinstance(pods, list):
            failing_pod = pods[0].get("pod_name", "failing pod")

        return (
            "You are a Kubernetes SRE Log Diagnostics Specialist.\n"
            f"Failing Workload Target: {context.target_workload or failing_pod}\n"
            "Action Rules:\n"
            f"1. Fetch crash logs by calling 'get_pod_logs' with action_args: {{\"namespace\": \"{context.target_namespace}\", \"pod_name\": \"{failing_pod}\"}}.\n"
            "2. If logs contain OutOfMemoryError, set root_cause_isolated=True, root_cause_summary='OutOfMemoryError', recommended_action='patch_memory'."
        )

    def get_response_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "reasoning": {"type": "string"},
                "action": {"type": "string", "enum": ["get_pod_logs", "get_pod_events", "none"]},
                "action_args": {
                    "type": "object",
                    "properties": {
                        "namespace": {"type": "string"},
                        "pod_name": {"type": "string"}
                    },
                    "required": ["namespace", "pod_name"]
                },
                "root_cause_isolated": {"type": "boolean"},
                "root_cause_summary": {"type": "string"},
                "recommended_action": {"type": "string", "enum": ["patch_memory", "restart", "none"]}
            },
            "required": ["reasoning", "action", "action_args", "root_cause_isolated"]
        }

    def evaluate_transition(
        self,
        context: AgentContext,
        decision: Dict[str, Any],
        action_output: Optional[ToolResult]
    ) -> AgentState:
        if action_output and action_output.success and action_output.output:
            log_text = str(action_output.output)
            context.blackboard["last_log_snippet"] = log_text
            if "OutOfMemoryError" in log_text or "OOMKilled" in log_text or "Java heap space" in log_text:
                context.blackboard["root_cause"] = "MEMORY_EXHAUSTION_OOM"
                context.blackboard["recommended_action"] = "patch_memory"
                return AgentState.REMEDIATE

        if decision.get("root_cause_isolated"):
            context.blackboard["root_cause"] = decision.get("root_cause_summary", "Diagnosed")
            context.blackboard["recommended_action"] = decision.get("recommended_action", "patch_memory")
            return AgentState.REMEDIATE

        if context.state_step_count >= context.max_steps_per_state:
            return AgentState.FAILED

        return AgentState.INVESTIGATE
