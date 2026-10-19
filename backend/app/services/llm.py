"""Async client for the local Ollama HTTP API."""

import logging
from typing import Any

import httpx

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)


class OllamaUnavailableError(RuntimeError):
    pass


class OllamaModelMissingError(RuntimeError):
    pass


class OllamaResponseError(RuntimeError):
    pass


class OllamaClient:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def _get_client(self, timeout_seconds: float | None = None) -> httpx.AsyncClient:
        return httpx.AsyncClient(timeout=httpx.Timeout(timeout_seconds or self.settings.ollama_timeout_seconds))

    async def list_models(self, timeout_seconds: float | None = None) -> list[str]:
        try:
            async with self._get_client(timeout_seconds) as client:
                response = await client.get(f"{self.settings.ollama_base_url}/api/tags")
                response.raise_for_status()
                payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise OllamaUnavailableError("Ollama is not reachable at the configured local URL.") from exc
        if not isinstance(payload, dict):
            raise OllamaResponseError("Ollama returned an invalid model list.")
        models = payload.get("models", [])
        if not isinstance(models, list):
            raise OllamaResponseError("Ollama returned an invalid model list.")
        return [str(item.get("name", "")) for item in models if isinstance(item, dict)]

    async def model_available(self) -> bool:
        names = await self.list_models()
        expected = self.settings.ollama_model
        normalized_names = {name if ":" in name else f"{name}:latest" for name in names}
        normalized_expected = expected if ":" in expected else f"{expected}:latest"
        return normalized_expected in normalized_names

    async def chat(self, messages: list[dict[str, str]]) -> tuple[str, dict[str, Any]]:
        """Generate a reply without pulling a missing model automatically."""
        try:
            async with self._get_client() as client:
                response = await client.post(
                    f"{self.settings.ollama_base_url}/api/chat",
                    json={
                        "model": self.settings.ollama_model,
                        "messages": messages,
                        "stream": False,
                        "options": {
                            "temperature": self.settings.ollama_temperature,
                            "num_ctx": self.settings.ollama_num_ctx,
                        },
                    },
                )
        except httpx.TimeoutException as exc:
            raise OllamaUnavailableError("Ollama did not respond before the request timed out.") from exc
        except httpx.HTTPError as exc:
            raise OllamaUnavailableError("Ollama is not reachable at the configured local URL.") from exc

        if response.status_code == 404:
            raise OllamaModelMissingError(
                f"Ollama model '{self.settings.ollama_model}' is missing. Pull it with 'ollama pull {self.settings.ollama_model}'."
            )
        if response.is_error:
            detail = response.text[:300]
            if "model" in detail.lower() and ("not found" in detail.lower() or "pull" in detail.lower()):
                raise OllamaModelMissingError(
                    f"Ollama model '{self.settings.ollama_model}' is missing. Pull it with 'ollama pull {self.settings.ollama_model}'."
                )
            raise OllamaResponseError(f"Ollama returned HTTP {response.status_code}.")

        try:
            payload = response.json()
            text = payload["message"]["content"]
        except (ValueError, KeyError, TypeError) as exc:
            raise OllamaResponseError("Ollama returned a malformed chat response.") from exc
        if not isinstance(text, str) or not text.strip():
            raise OllamaResponseError("Ollama returned an empty reply.")
        return text.strip(), payload


ollama_client = OllamaClient()
