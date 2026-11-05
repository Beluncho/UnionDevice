from __future__ import annotations

import asyncio
from typing import Any

import httpx

from backend.app.config import Settings
from backend.app.errors import (
    ProviderConfigurationError,
    ProviderRequestError,
    ProviderTimeoutError,
)
from backend.app.providers.base import ProviderResponse


class OpenAICompatibleProvider:
    def __init__(self, settings: Settings, client: httpx.AsyncClient | None = None) -> None:
        self._settings = settings
        self._owns_client = client is None
        proxy = (
            settings.llm_http_proxy_url.get_secret_value()
            if settings.llm_http_proxy_url
            else None
        )
        self._client = client or httpx.AsyncClient(
            timeout=settings.llm_timeout_seconds,
            proxy=proxy,
            trust_env=False,
        )

    async def generate(self, messages: list[dict[str, str]]) -> ProviderResponse:
        if not self._settings.llm_api_key or not self._settings.llm_model:
            raise ProviderConfigurationError()
        api_key = self._settings.llm_api_key.get_secret_value()
        if not api_key or api_key == "replace-me":
            raise ProviderConfigurationError()

        url = f"{self._settings.llm_base_url}/chat/completions"
        payload = {
            "model": self._settings.llm_model,
            "messages": messages,
            "temperature": 0.2,
        }
        headers = {"Authorization": f"Bearer {api_key}"}

        for attempt in range(2):
            try:
                response = await self._client.post(url, headers=headers, json=payload)
            except httpx.TimeoutException as exc:
                raise ProviderTimeoutError() from exc
            except httpx.HTTPError as exc:
                raise ProviderRequestError() from exc

            if response.status_code in {429, 500, 502, 503, 504} and attempt == 0:
                await asyncio.sleep(0.2)
                continue
            if response.is_error:
                raise ProviderRequestError(details={"upstream_status": response.status_code})

            try:
                data: dict[str, Any] = response.json()
                content = data["choices"][0]["message"]["content"]
            except (ValueError, KeyError, IndexError, TypeError) as exc:
                raise ProviderRequestError(details={"reason": "unexpected_response_shape"}) from exc
            if not isinstance(content, str) or not content.strip():
                raise ProviderRequestError(details={"reason": "empty_content"})
            return ProviderResponse(content=content, model=data.get("model"))

        raise ProviderRequestError()

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

