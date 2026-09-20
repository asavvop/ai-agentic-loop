"""
Native Local Ollama Client implementing ILLMClient without Docker dependencies.
"""
import json
import logging
import urllib.error
import urllib.request
from typing import Any, Dict
from src.core.interfaces import ILLMClient

logger = logging.getLogger("LocalOllamaClient")


class LocalOllamaClient(ILLMClient):
    """
    Direct HTTP client for local inference servers (e.g. Ollama at localhost:11434).
    """

    def __init__(
        self,
        endpoint: str = "http://localhost:11434/api/chat",
        model: str = "llama3.1",
        timeout: int = 30
    ):
        self._endpoint = endpoint
        self._model = model
        self._timeout = timeout

    def generate_structured_decision(
        self,
        system_prompt: str,
        user_prompt: str,
        response_schema: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Sends structured JSON prompt to local Ollama instance."""
        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "format": response_schema,
            "stream": False,
            "options": {"temperature": 0.0}
        }

        req = urllib.request.Request(
            self._endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )

        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                raw_data = json.loads(resp.read().decode("utf-8"))
                message_content = raw_data.get("message", {}).get("content", "{}")
                return json.loads(message_content)
        except urllib.error.URLError as e:
            logger.error(f"Failed to communicate with local model endpoint {self._endpoint}: {e}")
            raise ConnectionError(
                f"Local model inference unavailable at {self._endpoint}. "
                "Ensure local Ollama service is active."
            ) from e
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse structured JSON from model: {e}")
            return {"reasoning": "JSON parse error", "action": None}
