"""
Production entrypoint for running the continuous Agent Daemon.
"""
import json
import logging
import signal
import sys
from src.core.context import AgentState
from src.core.fsm_runner import FSMRunner
from src.handlers.triage_handler import TriageStateHandler
from src.handlers.investigate_handler import InvestigateStateHandler
from src.handlers.remediation_handler import RemediationStateHandler
from src.handlers.verify_handler import VerifyStateHandler
from src.clients.local_ollama_client import LocalOllamaClient
from src.clients.live_kubectl_gateway import LiveKubectlGateway
from src.daemon.config import DaemonConfig
from src.daemon.polling_watcher import PollingClusterWatcher
from src.daemon.daemon_engine import DaemonEngine
from src.daemon.interfaces import IDaemonObserver

logging.basicConfig(level=logging.INFO, format="%(asctime)s [AGENT-DAEMON] %(message)s")
logger = logging.getLogger("DaemonMain")


class LoggingObserver(IDaemonObserver):
    """Logs detailed lifecycle events and audit cards for the self-healing daemon."""
    def on_cycle_start(self, namespace: str) -> None:
        logger.debug(f"Audit cycle started for {namespace}")

    def on_self_healing_triggered(self, namespace: str, anomalies: list) -> None:
        logger.warning(f"==================================================")
        logger.warning(f"  ANOMALIES DETECTED: {len(anomalies)} failing pod(s) in '{namespace}'")
        for a in anomalies:
            logger.warning(f"    - Pod: {a.get('pod_name')} | Workload: {a.get('workload')} | Status: {a.get('status')} | Restarts: {a.get('restart_count')} | LastState: {a.get('last_state')}")
        logger.warning(f"  Triggering FSM Self-Healing Engine...")
        logger.warning(f"==================================================")

    def on_self_healing_completed(self, final_context) -> None:
        logger.info(f"==================================================")
        logger.info(f"  HEALING SUMMARY: Final State: {final_context.state.name} in {final_context.step_count} steps")
        logger.info(f"  Diagnosed Root Cause: {final_context.blackboard.get('root_cause', 'N/A')}")
        logger.info(f"  Remediation Action:   {json.dumps(final_context.blackboard.get('remediation_result', {}))}")
        logger.info(f"  Post-Check Status:    {json.dumps(final_context.blackboard.get('final_verification', {}))}")
        logger.info(f"==================================================")


def main():
    config = DaemonConfig.from_env()
    logger.info(f"Booting Agent Daemon | Namespace: {config.target_namespace} | Endpoint: {config.llm_endpoint}")

    tool_gateway = LiveKubectlGateway(kubeconfig=config.kubeconfig_path if config.kubeconfig_path else None)
    llm_client = LocalOllamaClient(endpoint=config.llm_endpoint, model=config.llm_model)

    handlers = {
        AgentState.TRIAGE: TriageStateHandler(),
        AgentState.INVESTIGATE: InvestigateStateHandler(),
        AgentState.REMEDIATE: RemediationStateHandler(),
        AgentState.VERIFY: VerifyStateHandler()
    }

    fsm_runner = FSMRunner(llm_client=llm_client, tool_gateway=tool_gateway, handlers=handlers, global_max_steps=12)
    watcher = PollingClusterWatcher(tool_gateway=tool_gateway)
    observer = LoggingObserver()

    engine = DaemonEngine(
        watcher=watcher,
        fsm_runner=fsm_runner,
        config=config,
        observers=[observer]
    )

    # Graceful shutdown handling
    def handle_sigterm(signum, frame):
        logger.info("Received termination signal. Shutting down daemon...")
        engine.stop()
        sys.exit(0)

    signal.signal(signal.SIGTERM, handle_sigterm)
    signal.signal(signal.SIGINT, handle_sigterm)

    engine.start()


if __name__ == "__main__":
    main()
