"""
Unit tests for RemediationStateHandler.
"""
from src.core.context import AgentContext, AgentState
from src.core.interfaces import ToolResult
from src.handlers.remediation_handler import RemediationStateHandler


def test_remediation_handler_properties():
    handler = RemediationStateHandler()
    assert handler.state == AgentState.REMEDIATE
    assert "patch_deployment_resources" in handler.allowed_tools
    assert "restart_deployment" in handler.allowed_tools


def test_remediation_transitions_to_verify_on_success():
    handler = RemediationStateHandler()
    ctx = AgentContext(target_namespace="production", target_workload="payment-service")
    ctx.blackboard["recommended_action"] = "patch_memory"
    decision = {
        "reasoning": "Patching memory to 2Gi",
        "action": "patch_deployment_resources",
        "action_args": {"namespace": "production", "deployment_name": "payment-service", "memory_limit": "2Gi"},
        "remediation_initiated": True
    }
    tool_out = ToolResult(success=True, output={"status": "Patched", "new_memory_limit": "2Gi"})

    next_state = handler.evaluate_transition(ctx, decision, tool_out)
    assert next_state == AgentState.VERIFY
    assert "remediation_result" in ctx.blackboard
