"""
Unit tests for FSMRunner with deterministic mocks.
"""
from typing import Any, Dict, List, Optional
from src.core.context import AgentContext, AgentState
from src.core.interfaces import ILLMClient, IToolGateway, ToolResult
from src.core.fsm_runner import FSMRunner
from src.handlers.base_handler import BaseStateHandler


class MockLLM(ILLMClient):
    def __init__(self, scripted_responses: List[Dict[str, Any]]):
        self._responses = list(scripted_responses)

    def generate_structured_decision(
        self, system_prompt: str, user_prompt: str, response_schema: Dict[str, Any]
    ) -> Dict[str, Any]:
        if not self._responses:
            return {"reasoning": "default", "action": None}
        return self._responses.pop(0)


class MockToolGateway(IToolGateway):
    def __init__(self, tool_outputs: Optional[Dict[str, Any]] = None):
        self.tool_outputs = tool_outputs or {}
        self.executed_calls: List[tuple] = []

    def get_available_tools(self) -> List[str]:
        return list(self.tool_outputs.keys())

    def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> ToolResult:
        self.executed_calls.append((tool_name, arguments))
        if tool_name in self.tool_outputs:
            return ToolResult(success=True, output=self.tool_outputs[tool_name])
        return ToolResult(success=False, output=None, error_message="Tool not found")


class DummyTriageHandler(BaseStateHandler):
    @property
    def state(self) -> AgentState:
        return AgentState.TRIAGE

    @property
    def allowed_tools(self) -> List[str]:
        return ["list_unhealthy_pods"]

    def build_system_prompt(self, context: AgentContext) -> str:
        return "Triage prompt"

    def get_response_schema(self) -> Dict[str, Any]:
        return {"type": "object"}

    def evaluate_transition(
        self, context: AgentContext, decision: Dict[str, Any], action_output: Optional[ToolResult]
    ) -> AgentState:
        if decision.get("action") == "list_unhealthy_pods" and action_output and action_output.output:
            return AgentState.INVESTIGATE
        return AgentState.RESOLVED


class DummyInvestigateHandler(BaseStateHandler):
    @property
    def state(self) -> AgentState:
        return AgentState.INVESTIGATE

    @property
    def allowed_tools(self) -> List[str]:
        return ["get_pod_logs"]

    def build_system_prompt(self, context: AgentContext) -> str:
        return "Investigate prompt"

    def get_response_schema(self) -> Dict[str, Any]:
        return {"type": "object"}

    def evaluate_transition(
        self, context: AgentContext, decision: Dict[str, Any], action_output: Optional[ToolResult]
    ) -> AgentState:
        return AgentState.RESOLVED


def test_fsm_runner_happy_path():
    llm = MockLLM([
        {"reasoning": "Found issue", "action": "list_unhealthy_pods", "action_args": {"namespace": "production"}},
        {"reasoning": "Investigated logs", "action": "get_pod_logs", "action_args": {"pod_name": "pod-1"}}
    ])
    tools = MockToolGateway({
        "list_unhealthy_pods": [{"pod_name": "pod-1", "reason": "OOMKilled"}],
        "get_pod_logs": "java.lang.OutOfMemoryError"
    })
    handlers = {
        AgentState.TRIAGE: DummyTriageHandler(),
        AgentState.INVESTIGATE: DummyInvestigateHandler()
    }

    runner = FSMRunner(llm, tools, handlers)
    ctx = AgentContext(target_namespace="production")
    result = runner.run(ctx)

    assert result.state == AgentState.RESOLVED
    assert result.step_count == 2
    assert len(tools.executed_calls) == 2


def test_fsm_runner_guards_unauthorized_tool():
    llm = MockLLM([
        {"reasoning": "Attempting illegal action", "action": "delete_cluster", "action_args": {}}
    ])
    tools = MockToolGateway({"delete_cluster": "Cluster deleted"})
    handlers = {
        AgentState.TRIAGE: DummyTriageHandler()
    }

    runner = FSMRunner(llm, tools, handlers)
    ctx = AgentContext(target_namespace="production")
    result = runner.run(ctx)

    # Tool should not have been executed on the gateway
    assert len(tools.executed_calls) == 0
    assert result.state == AgentState.RESOLVED
