"""
Unit tests for DaemonConfig.
"""
import os
from unittest.mock import patch
from src.daemon.config import DaemonConfig


def test_daemon_config_from_env_defaults():
    with patch.dict(os.environ, {}, clear=True):
        config = DaemonConfig.from_env()
        assert config.target_namespace == "production"
        assert config.poll_interval_seconds == 15
        assert config.llm_model == "llama3.1:latest"


def test_daemon_config_from_custom_env():
    env = {
        "TARGET_NAMESPACE": "staging",
        "POLL_INTERVAL_SECONDS": "30",
        "LLM_ENDPOINT": "http://custom-ollama:11434/api/chat",
        "LLM_MODEL": "qwen2.5:3b"
    }
    with patch.dict(os.environ, env, clear=True):
        config = DaemonConfig.from_env()
        assert config.target_namespace == "staging"
        assert config.poll_interval_seconds == 30
        assert config.llm_endpoint == "http://custom-ollama:11434/api/chat"
        assert config.llm_model == "qwen2.5:3b"
