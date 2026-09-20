"""
Unit tests for LocalOllamaClient.
"""
import io
import json
from unittest.mock import MagicMock, patch
from src.clients.local_ollama_client import LocalOllamaClient


def test_generate_structured_decision_success():
    client = LocalOllamaClient(endpoint="http://localhost:11434/api/chat", model="llama3.1")
    mock_response_payload = {
        "message": {
            "content": json.dumps({"reasoning": "Detected error", "action": "get_pod_logs"})
        }
    }
    mock_bytes = json.dumps(mock_response_payload).encode("utf-8")

    mock_resp = MagicMock()
    mock_resp.read.return_value = mock_bytes
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        decision = client.generate_structured_decision(
            system_prompt="sys",
            user_prompt="usr",
            response_schema={"type": "object"}
        )

    assert decision["reasoning"] == "Detected error"
    assert decision["action"] == "get_pod_logs"
