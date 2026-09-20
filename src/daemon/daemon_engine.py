"""
Daemon Engine implementing Single Responsibility and Dependency Inversion.
"""
import logging
import time
from typing import Callable, List, Optional
from src.core.context import AgentContext
from src.core.fsm_runner import FSMRunner
from src.daemon.config import DaemonConfig
from src.daemon.interfaces import IClusterWatcher, IDaemonObserver

logger = logging.getLogger("DaemonEngine")


class DaemonEngine:
    """
    Coordinates continuous observation cycles, anomaly evaluation, and FSM invocation.
    """

    def __init__(
        self,
        watcher: IClusterWatcher,
        fsm_runner: FSMRunner,
        config: DaemonConfig,
        observers: Optional[List[IDaemonObserver]] = None,
        sleeper: Callable[[int], None] = time.sleep
    ):
        self._watcher = watcher
        self._fsm_runner = fsm_runner
        self._config = config
        self._observers = observers or []
        self._sleeper = sleeper
        self._running = False

    def run_cycle(self) -> Optional[AgentContext]:
        """Executes a single observation and healing tick."""
        namespace = self._config.target_namespace
        for obs in self._observers:
            obs.on_cycle_start(namespace)

        anomalies = self._watcher.detect_anomalies(namespace)
        if not anomalies:
            logger.debug(f"Namespace '{namespace}' is healthy. No action required.")
            return None

        logger.warning(f"Detected {len(anomalies)} anomalous pod(s) in '{namespace}'. Triggering FSM...")
        for obs in self._observers:
            obs.on_self_healing_triggered(namespace, anomalies)

        context = AgentContext(target_namespace=namespace)
        final_context = self._fsm_runner.run(context)

        for obs in self._observers:
            obs.on_self_healing_completed(final_context)

        return final_context

    def start(self, max_cycles: Optional[int] = None) -> None:
        """Starts the continuous loop with configurable cycle count for testing/daemon mode."""
        self._running = True
        cycles_completed = 0
        logger.info(f"Daemon started. Target Namespace: {self._config.target_namespace} | Interval: {self._config.poll_interval_seconds}s")

        while self._running:
            try:
                self.run_cycle()
            except Exception as e:
                logger.error(f"Unhandled error in daemon cycle: {e}")

            cycles_completed += 1
            if max_cycles is not None and cycles_completed >= max_cycles:
                logger.info(f"Reached max cycles limit ({max_cycles}). Stopping daemon.")
                break

            self._sleeper(self._config.poll_interval_seconds)

    def stop(self) -> None:
        """Signals the daemon to gracefully shut down."""
        self._running = False
