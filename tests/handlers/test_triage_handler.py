"""
Unit tests for TriageStateHandler.
"""
from src.core.context import AgentContext, AgentState
from src.core.interfaces import ToolResult
from src.handlers.triage_handler import TriageStateHandler


def test_triage_handler_properties():
    handler = TriageStateHandler()
    assert handler.state == AgentState.TRIAGE
    assert "list_unhealthy_pods" in handler.allowed_tools
    schema = handler.get_response_schema()
    assert "has_unhealthy_workloads" in schema["required"]


def test_triage_transitions_to_investigate_when_unhealthy_pods_found():
    handler = TriageStateHandler()
    ctx = AgentContext(target_namespace="production")
    decision = {
        "reasoning": "Detected 1 failing pod",
        "action": "list_unhealthy_pods",
        "action_args": {"namespace": "production"},
        "has_unhealthy_workloads": True
    }
    tool_out = ToolResult(
        success=True,
        output=[{"pod_name": "payment-service-8f2a", "workload": "payment-service", "status": "CrashLoopBackOff"}]
    )

    next_state = handler.evaluate_transition(ctx, decision, tool_out)
    assert next_state == AgentState.INVESTIGATE
    assert "unhealthy_pods" in ctx.blackboard
    assert ctx.target_workload == "payment-service"


def test_triage_transitions_to_resolved_when_all_healthy():
    handler = TriageStateHandler()
    ctx = AgentContext(target_namespace="production")
    decision = {
        "reasoning": "All pods healthy",
        "action": "list_unhealthy_pods",
        "action_args": {"namespace": "production"},
        "has_unhealthy_workloads": False
    }
    tool_out = ToolResult(success=True, output=[])

    next_state = handler.evaluate_transition(ctx, decision, tool_out)
    assert next_state == AgentState.RESOLVED
