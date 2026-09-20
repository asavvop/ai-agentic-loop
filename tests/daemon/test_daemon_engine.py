"""
Unit tests for DaemonEngine with deterministic mocks.
"""
from typing import Any, Dict, List
from src.core.context import AgentContext, AgentState
from src.core.interfaces import ILLMClient, IToolGateway, ToolResult
from src.core.fsm_runner import FSMRunner
from src.daemon.config import DaemonConfig
from src.daemon.daemon_engine import DaemonEngine
from src.daemon.interfaces import IClusterWatcher, IDaemonObserver
from src.handlers.base_handler import BaseStateHandler


class MockClusterWatcher(IClusterWatcher):
    def __init__(self, anomaly_sequences: List[List[Dict[str, Any]]]):
        self._sequences = list(anomaly_sequences)

    def detect_anomalies(self, namespace: str) -> List[Dict[str, Any]]:
        if self._sequences:
            return self._sequences.pop(0)
        return []


class MockObserver(IDaemonObserver):
    def __init__(self):
        self.cycle_starts = 0
        self.triggers = 0
        self.completions = 0

    def on_cycle_start(self, namespace: str) -> None:
        self.cycle_starts += 1

    def on_self_healing_triggered(self, namespace: str, anomalies: List[Dict[str, Any]]) -> None:
        self.triggers += 1

    def on_self_healing_completed(self, final_context: AgentContext) -> None:
        self.completions += 1


class DummyTriage(BaseStateHandler):
    @property
    def state(self) -> AgentState:
        return AgentState.TRIAGE

    @property
    def allowed_tools(self) -> List[str]:
        return []

    def build_system_prompt(self, context: AgentContext) -> str:
        return "Triage"

    def get_response_schema(self) -> Dict[str, Any]:
        return {"type": "object"}

    def evaluate_transition(self, context: AgentContext, decision: Dict[str, Any], action_output: Any) -> AgentState:
        return AgentState.RESOLVED


class MockLLM(ILLMClient):
    def generate_structured_decision(self, s: str, u: str, sc: dict) -> dict:
        return {"reasoning": "done", "action": None}


class MockGateway(IToolGateway):
    def get_available_tools(self) -> List[str]:
        return []

    def execute_tool(self, n: str, a: dict) -> ToolResult:
        return ToolResult(success=True, output={})


def test_daemon_cycle_skips_when_healthy():
    watcher = MockClusterWatcher([[]])  # No anomalies
    runner = FSMRunner(MockLLM(), MockGateway(), {AgentState.TRIAGE: DummyTriage()})
    config = DaemonConfig("production", 10, "http://localhost:11434/api/chat", "llama3.1", "")
    observer = MockObserver()

    engine = DaemonEngine(watcher, runner, config, observers=[observer])
    results = engine.run_cycle()

    assert results == []
    assert observer.cycle_starts == 1
    assert observer.triggers == 0
    assert observer.completions == 0


def test_daemon_cycle_triggers_fsm_when_anomalies_found():
    watcher = MockClusterWatcher([[{"pod_name": "pod-1", "status": "OOMKilled"}]])
    runner = FSMRunner(MockLLM(), MockGateway(), {AgentState.TRIAGE: DummyTriage()})
    config = DaemonConfig("production", 10, "http://localhost:11434/api/chat", "llama3.1", "")
    observer = MockObserver()

    engine = DaemonEngine(watcher, runner, config, observers=[observer])
    results = engine.run_cycle()

    assert len(results) == 1
    assert results[0].state == AgentState.RESOLVED
    assert observer.cycle_starts == 1
    assert observer.triggers == 1
    assert observer.completions == 1


def test_daemon_cycle_multi_namespace():
    watcher = MockClusterWatcher([
        [{"pod_name": "pod-1", "status": "OOMKilled"}],  # production has anomaly
        []                                               # default is healthy
    ])
    runner = FSMRunner(MockLLM(), MockGateway(), {AgentState.TRIAGE: DummyTriage()})
    config = DaemonConfig("production,default", 10, "http://localhost:11434/api/chat", "llama3.1", "")
    observer = MockObserver()

    engine = DaemonEngine(watcher, runner, config, observers=[observer])
    results = engine.run_cycle()

    assert len(results) == 1
    assert observer.cycle_starts == 2
    assert observer.triggers == 1


def test_daemon_engine_start_bounded_cycles():
    watcher = MockClusterWatcher([[], []])
    runner = FSMRunner(MockLLM(), MockGateway(), {AgentState.TRIAGE: DummyTriage()})
    config = DaemonConfig("production", 10, "http://localhost:11434/api/chat", "llama3.1", "")
    slept_times = []

    def mock_sleep(seconds: int):
        slept_times.append(seconds)

    engine = DaemonEngine(watcher, runner, config, sleeper=mock_sleep)
    engine.start(max_cycles=2)

    assert len(slept_times) == 1
    assert slept_times == [10]
