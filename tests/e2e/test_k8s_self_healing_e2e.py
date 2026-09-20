"""
End-to-End Autonomous Diagnostics & Self-Healing Loop Test.
"""
from typing import Any, Dict, List
from src.core.context import AgentContext, AgentState
from src.core.interfaces import ILLMClient
from src.core.fsm_runner import FSMRunner
from src.handlers.triage_handler import TriageStateHandler
from src.handlers.investigate_handler import InvestigateStateHandler
from src.handlers.remediation_handler import RemediationStateHandler
from src.handlers.verify_handler import VerifyStateHandler
from src.clients.mcp_stdio_gateway import DirectMCPToolGateway
import src.server.mcp_k8s_server as server_module
from src.server.k8s_telemetry import K8sClusterTelemetry


class ScriptedE2ELLM(ILLMClient):
    """Simulates an LLM agent reasoning sequentially through the FSM states."""

    def __init__(self):
        self.decisions = [
            # 1. TRIAGE step
            {
                "reasoning": "Inspecting namespace for degraded workloads.",
                "action": "list_unhealthy_pods",
                "action_args": {"namespace": "production"},
                "has_unhealthy_workloads": True
            },
            # 2. INVESTIGATE step
            {
                "reasoning": "Pulling crash logs for failing pod to isolate root cause.",
                "action": "get_pod_logs",
                "action_args": {"namespace": "production", "pod_name": "payment-service-8f2a"},
                "root_cause_isolated": True,
                "root_cause_summary": "Java heap space OutOfMemoryError",
                "recommended_action": "patch_memory"
            },
            # 3. REMEDIATE step
            {
                "reasoning": "Patching memory limit to 2Gi to resolve OOM.",
                "action": "patch_deployment_resources",
                "action_args": {
                    "namespace": "production",
                    "deployment_name": "payment-service",
                    "memory_limit": "2Gi"
                },
                "remediation_initiated": True
            },
            # 4. VERIFY step
            {
                "reasoning": "Checking deployment replica status post-patch.",
                "action": "get_deployment_status",
                "action_args": {
                    "namespace": "production",
                    "deployment_name": "payment-service"
                },
                "is_fully_healthy": True
            }
        ]

    def generate_structured_decision(
        self, system_prompt: str, user_prompt: str, response_schema: Dict[str, Any]
    ) -> Dict[str, Any]:
        if self.decisions:
            return self.decisions.pop(0)
        return {"reasoning": "Terminal state", "action": None}


def test_autonomous_k8s_self_healing_e2e():
    # Reset cluster telemetry
    server_module.telemetry = K8sClusterTelemetry()

    tool_gateway = DirectMCPToolGateway()
    llm_client = ScriptedE2ELLM()

    handlers = {
        AgentState.TRIAGE: TriageStateHandler(),
        AgentState.INVESTIGATE: InvestigateStateHandler(),
        AgentState.REMEDIATE: RemediationStateHandler(),
        AgentState.VERIFY: VerifyStateHandler()
    }

    runner = FSMRunner(
        llm_client=llm_client,
        tool_gateway=tool_gateway,
        handlers=handlers,
        global_max_steps=10
    )

    ctx = AgentContext(target_namespace="production")
    result = runner.run(ctx)

    # Assert final resolution
    assert result.state == AgentState.RESOLVED
    assert result.step_count == 4
    assert result.blackboard.get("root_cause") == "MEMORY_EXHAUSTION_OOM"
    assert result.blackboard.get("recommended_action") == "patch_memory"

    final_status = result.blackboard.get("final_verification")
    assert final_status["status"] == "Healthy"
    assert final_status["readyReplicas"] == 3
    assert final_status["memory_limit"] == "2Gi"
