from __future__ import annotations

import json

import httpx
import pytest
from pydantic import SecretStr

from backend.app.config import Settings
from backend.app.errors import ProviderRequestError
from backend.app.providers.openai_compatible import OpenAICompatibleProvider


@pytest.mark.asyncio
async def test_provider_uses_configured_base_url_model_and_bearer_token() -> None:
    captured: dict = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["authorization"] = request.headers["Authorization"]
        captured["payload"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={"model": "gateway-model", "choices": [{"message": {"content": "{}"}}]},
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    settings = Settings(
        llm_api_key=SecretStr("secret-value"),
        llm_base_url="https://gateway.example/v1/",
        llm_model="gateway-model",
    )
    provider = OpenAICompatibleProvider(settings, client=client)
    response = await provider.generate([{"role": "user", "content": "hello"}])
    await client.aclose()

    assert captured["url"] == "https://gateway.example/v1/chat/completions"
    assert captured["authorization"] == "Bearer secret-value"
    assert captured["payload"]["model"] == "gateway-model"
    assert response.content == "{}"


@pytest.mark.asyncio
async def test_provider_retries_transient_status_once() -> None:
    calls = 0

    async def handler(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(429, json={"error": "rate limited"})
        return httpx.Response(200, json={"choices": [{"message": {"content": "{}"}}]})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = OpenAICompatibleProvider(
        Settings(llm_api_key=SecretStr("key"), llm_model="model"),
        client=client,
    )
    await provider.generate([{"role": "user", "content": "hello"}])
    await client.aclose()
    assert calls == 2


@pytest.mark.asyncio
async def test_provider_does_not_return_upstream_body_on_error() -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(401, text="sensitive upstream body")

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = OpenAICompatibleProvider(
        Settings(llm_api_key=SecretStr("key"), llm_model="model"),
        client=client,
    )
    with pytest.raises(ProviderRequestError) as error:
        await provider.generate([{"role": "user", "content": "hello"}])
    await client.aclose()
    assert error.value.details == {"upstream_status": 401}

