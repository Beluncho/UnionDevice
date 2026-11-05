from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class ProviderResponse:
    content: str
    model: str | None = None


class LLMProvider(Protocol):
    async def generate(self, messages: list[dict[str, str]]) -> ProviderResponse: ...

