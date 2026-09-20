"""
Unit tests for InvestigateStateHandler.
"""
from src.core.context import AgentContext, AgentState
from src.core.interfaces import ToolResult
from src.handlers.investigate_handler import InvestigateStateHandler


def test_investigate_handler_properties():
    handler = InvestigateStateHandler()
    assert handler.state == AgentState.INVESTIGATE
    assert "get_pod_logs" in handler.allowed_tools
    assert "get_pod_events" in handler.allowed_tools


def test_investigate_transitions_to_remediate_on_oom():
    handler = InvestigateStateHandler()
    ctx = AgentContext(target_namespace="production", target_workload="payment-service")
    decision = {"reasoning": "Inspecting logs", "action": "get_pod_logs", "root_cause_isolated": False}
    tool_out = ToolResult(
        success=True,
        output="Exception in thread main: java.lang.OutOfMemoryError: Java heap space"
    )

    next_state = handler.evaluate_transition(ctx, decision, tool_out)
    assert next_state == AgentState.REMEDIATE
    assert ctx.blackboard.get("root_cause") == "MEMORY_EXHAUSTION_OOM"
    assert ctx.blackboard.get("recommended_action") == "patch_memory"


def test_investigate_continues_if_no_root_cause_yet():
    handler = InvestigateStateHandler()
    ctx = AgentContext(target_namespace="production", target_workload="payment-service")
    decision = {"reasoning": "Still inspecting", "action": "get_pod_logs", "root_cause_isolated": False}
    tool_out = ToolResult(success=True, output="Starting service...")

    next_state = handler.evaluate_transition(ctx, decision, tool_out)
    assert next_state == AgentState.INVESTIGATE
