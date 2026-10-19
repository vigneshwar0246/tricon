import json

import httpx
import pytest

from app.core.config import Settings
from app.services.llm import OllamaClient, OllamaModelMissingError


@pytest.mark.asyncio
async def test_ollama_connection_reuse_and_generation_limit() -> None:
    requests: list[dict] = []

    def respond(request: httpx.Request) -> httpx.Response:
        requests.append(json.loads(request.content))
        return httpx.Response(200, json={"message": {"content": "real upstream text"}, "total_duration": 10_000_000})

    client = OllamaClient(Settings(ollama_num_predict=96))
    client._client = httpx.AsyncClient(transport=httpx.MockTransport(respond))
    connection = client._client
    try:
        assert (await client.chat([{"role": "user", "content": "Hello"}]))[0] == "real upstream text"
        assert (await client.chat([{"role": "user", "content": "Again"}]))[0] == "real upstream text"
        assert client._client is connection
        assert all(item["options"]["num_predict"] == 96 and item["keep_alive"] == "15m" for item in requests)
    finally:
        await client.close()
    assert connection.is_closed


@pytest.mark.asyncio
async def test_ollama_missing_model_is_reported_without_fabrication() -> None:
    client = OllamaClient()
    client._client = httpx.AsyncClient(transport=httpx.MockTransport(lambda _: httpx.Response(404)))
    try:
        with pytest.raises(OllamaModelMissingError):
            await client.chat([{"role": "user", "content": "Hello"}])
    finally:
        await client.close()
