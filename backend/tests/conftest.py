from __future__ import annotations

import json
from collections import deque

import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.config import Settings
from backend.app.main import create_app
from backend.app.providers.base import ProviderResponse


def valid_model_content(*, keys: list[str] | None = None, suffix: str = "") -> str:
    description = (
        "Прибор предназначен для работы с задачами измерения и контроля на основе "
        "предоставленных технических данных. Описание подготовлено как черновик для "
        "контент-менеджера и не добавляет неподтвержденных характеристик. "
        "Устройство можно рассматривать для специалистов, которым важно сопоставить "
        "назначение прибора с параметрами конкретного проекта. Перед публикацией следует "
        "проверить формулировки по техническому паспорту и внутренним требованиям каталога. "
    )
    description = (description * 3)[:900]
    payload = {
        "seo_title": f"testo 510 — дифференциальный манометр{suffix}",
        "seo_description": description,
        "key_characteristic_names": keys or ["Диапазон измерений", "Класс защиты"],
        "search_queries": [
            "testo 510 дифференциальный манометр",
            "манометр testo 510",
            "прибор измерения давления testo 510",
        ],
        "commercial_block": "Подходит специалистам для задач измерения и контроля давления.",
    }
    return json.dumps(payload, ensure_ascii=False)


class FakeProvider:
    def __init__(self, *contents: str) -> None:
        self.contents = deque(contents)
        self.calls: list[list[dict[str, str]]] = []

    async def generate(self, messages: list[dict[str, str]]) -> ProviderResponse:
        self.calls.append(messages)
        return ProviderResponse(content=self.contents.popleft())


@pytest.fixture
def product_payload() -> dict:
    return {
        "name": "testo 510",
        "manufacturer": "Testo",
        "specs": {"Диапазон измерений": "0 ... 100 гПа", "Класс защиты": "IP40"},
        "description": "Прибор измеряет дифференциальное давление.",
    }


async def api_client(provider: FakeProvider) -> AsyncClient:
    app = create_app(provider=provider, settings=Settings(llm_model="test-model"))
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")

