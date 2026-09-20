"""
Unit tests for AgentContext and AgentState.
"""
from src.core.context import AgentContext, AgentState


def test_agent_state_is_terminal():
    assert AgentState.RESOLVED.is_terminal is True
    assert AgentState.FAILED.is_terminal is True
    assert AgentState.TRIAGE.is_terminal is False
    assert AgentState.INVESTIGATE.is_terminal is False
    assert AgentState.REMEDIATE.is_terminal is False
    assert AgentState.VERIFY.is_terminal is False


def test_agent_context_initialization():
    ctx = AgentContext(target_namespace="production", target_workload="payment-service")
    assert ctx.target_namespace == "production"
    assert ctx.target_workload == "payment-service"
    assert ctx.state == AgentState.TRIAGE
    assert ctx.step_count == 0
    assert ctx.state_step_count == 0
    assert ctx.blackboard == {}
    assert ctx.execution_history == []


def test_agent_context_transition_resets_state_counter():
    ctx = AgentContext(target_namespace="production")
    ctx.increment_turn()
    ctx.increment_turn()
    assert ctx.step_count == 2
    assert ctx.state_step_count == 2

    ctx.transition_to(AgentState.INVESTIGATE)
    assert ctx.state == AgentState.INVESTIGATE
    assert ctx.step_count == 2
    assert ctx.state_step_count == 0


def test_agent_context_record_step():
    ctx = AgentContext(target_namespace="staging")
    ctx.increment_turn()
    decision = {"reasoning": "checking pods", "action": "list_pods"}
    ctx.record_step(AgentState.TRIAGE, AgentState.INVESTIGATE, decision, action_output={"unhealthy": 1})

    assert len(ctx.execution_history) == 1
    record = ctx.execution_history[0]
    assert record["step"] == 1
    assert record["from_state"] == "TRIAGE"
    assert record["to_state"] == "INVESTIGATE"
    assert record["decision"] == decision
    assert record["action_output"] == {"unhealthy": 1}
