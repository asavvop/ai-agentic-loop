"""
Unit tests for VerifyStateHandler.
"""
from src.core.context import AgentContext, AgentState
from src.core.interfaces import ToolResult
from src.handlers.verify_handler import VerifyStateHandler


def test_verify_handler_properties():
    handler = VerifyStateHandler()
    assert handler.state == AgentState.VERIFY
    assert "get_deployment_status" in handler.allowed_tools


def test_verify_transitions_to_resolved_when_healthy():
    handler = VerifyStateHandler()
    ctx = AgentContext(target_namespace="production", target_workload="payment-service")
    decision = {
        "reasoning": "Checking replicas",
        "action": "get_deployment_status",
        "action_args": {"namespace": "production", "deployment_name": "payment-service"},
        "is_fully_healthy": True
    }
    tool_out = ToolResult(
        success=True,
        output={"readyReplicas": 3, "desiredReplicas": 3, "status": "Healthy"}
    )

    next_state = handler.evaluate_transition(ctx, decision, tool_out)
    assert next_state == AgentState.RESOLVED
    assert "final_verification" in ctx.blackboard


def test_verify_transitions_to_investigate_if_unhealthy():
    handler = VerifyStateHandler()
    ctx = AgentContext(target_namespace="production", target_workload="payment-service")
    ctx.step_count = 3
    decision = {
        "reasoning": "Pods still not ready",
        "action": "get_deployment_status",
        "is_fully_healthy": False
    }
    tool_out = ToolResult(
        success=True,
        output={"readyReplicas": 0, "desiredReplicas": 3, "status": "Degraded"}
    )

    next_state = handler.evaluate_transition(ctx, decision, tool_out)
    assert next_state == AgentState.INVESTIGATE
