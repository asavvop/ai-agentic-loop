"""
Configuration management for the continuous Agent Daemon.
"""
from dataclasses import dataclass
import os
import subprocess


@dataclass(frozen=True)
class DaemonConfig:
    """Immutable daemon configuration loaded from environment or defaults."""
    target_namespace: str
    poll_interval_seconds: int
    llm_endpoint: str
    llm_model: str
    kubeconfig_path: str

    @classmethod
    def from_env(cls) -> "DaemonConfig":
        """Factory method loading configuration from environment variables."""
        target_namespace = os.getenv("TARGET_NAMESPACE", "production")
        poll_interval = int(os.getenv("POLL_INTERVAL_SECONDS", "15"))
        llm_model = os.getenv("LLM_MODEL", "llama3.1:latest")

        # Discover endpoint or default to host gateway
        endpoint = os.getenv("LLM_ENDPOINT")
        if not endpoint:
            gateway_ip = cls._discover_gateway_ip()
            endpoint = f"http://{gateway_ip}:11434/api/chat"

        # In-cluster service account takes precedence if running in a Pod
        if os.path.exists("/var/run/secrets/kubernetes.io/serviceaccount"):
            kubeconfig = ""
        else:
            kubeconfig = os.getenv("KUBECONFIG", "/etc/rancher/k3s/k3s.yaml")

        return cls(
            target_namespace=target_namespace,
            poll_interval_seconds=poll_interval,
            llm_endpoint=endpoint,
            llm_model=llm_model,
            kubeconfig_path=kubeconfig
        )

    @staticmethod
    def _discover_gateway_ip() -> str:
        try:
            res = subprocess.run(["ip", "route", "show", "default"], capture_output=True, text=True, check=True)
            tokens = res.stdout.strip().split()
            if len(tokens) >= 3 and tokens[0] == "default" and tokens[1] == "via":
                return tokens[2]
        except Exception:
            pass
        return "127.0.0.1"
