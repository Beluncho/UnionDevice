from __future__ import annotations

import json

import pytest

from backend.tests.conftest import FakeProvider, api_client, valid_model_content


@pytest.mark.asyncio
async def test_health_does_not_call_provider() -> None:
    provider = FakeProvider()
    async with await api_client(provider) as client:
        response = await client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert provider.calls == []


@pytest.mark.asyncio
async def test_examples_are_available_without_provider() -> None:
    provider = FakeProvider()
    async with await api_client(provider) as client:
        response = await client.get("/api/v1/examples")
    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [
        "testo-510",
        "testo-510.partial",
        "testo-830-t1",
    ]
    assert provider.calls == []


@pytest.mark.asyncio
async def test_generate_complete_product(product_payload: dict) -> None:
    provider = FakeProvider(valid_model_content())
    async with await api_client(provider) as client:
        response = await client.post("/api/v1/product-cards/generate", json=product_payload)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "draft_ready"
    assert body["quality"] == {"grounded": True, "retry_count": 0}
    assert body["draft"]["key_characteristics"][0] == {
        "name": "Диапазон измерений",
        "value": "0 ... 100 гПа",
    }
    assert body["request_id"]


@pytest.mark.asyncio
async def test_partial_product_is_marked_for_clarification(product_payload: dict) -> None:
    product_payload["description"] = None
    provider = FakeProvider(valid_model_content())
    async with await api_client(provider) as client:
        response = await client.post("/api/v1/product-cards/generate", json=product_payload)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "needs_clarification"
    assert body["missing_fields"] == ["description"]
    assert body["draft"]["markdown"].startswith("> ⚠️")


@pytest.mark.asyncio
async def test_insufficient_product_is_rejected_before_provider() -> None:
    provider = FakeProvider()
    async with await api_client(provider) as client:
        response = await client.post(
            "/api/v1/product-cards/generate",
            json={"name": "testo 510", "specs": {}, "description": None},
        )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "insufficient_product_data"
    assert provider.calls == []


@pytest.mark.asyncio
async def test_invalid_model_json_is_corrected_once(product_payload: dict) -> None:
    provider = FakeProvider("not-json", valid_model_content())
    async with await api_client(provider) as client:
        response = await client.post("/api/v1/product-cards/generate", json=product_payload)
    assert response.status_code == 200
    assert response.json()["quality"]["retry_count"] == 1
    assert len(provider.calls) == 2
    assert "Нарушения" in provider.calls[1][-1]["content"]


@pytest.mark.asyncio
async def test_invalid_model_response_after_retry_is_502(product_payload: dict) -> None:
    provider = FakeProvider("not-json", json.dumps({"seo_title": "x"}))
    async with await api_client(provider) as client:
        response = await client.post("/api/v1/product-cards/generate", json=product_payload)
    assert response.status_code == 502
    assert response.json()["error"]["code"] == "provider_invalid_response"


@pytest.mark.asyncio
async def test_invalid_model_response_for_partial_product_returns_clarification(
    product_payload: dict,
) -> None:
    product_payload["description"] = None
    provider = FakeProvider("not-json", json.dumps({"seo_title": "x"}))
    async with await api_client(provider) as client:
        response = await client.post("/api/v1/product-cards/generate", json=product_payload)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "needs_clarification"
    assert body["draft"] is None
    assert body["quality"] == {"grounded": False, "retry_count": 1}
    assert body["missing_fields"] == ["description"]


@pytest.mark.asyncio
async def test_ungrounded_technical_value_triggers_retry(product_payload: dict) -> None:
    bad = valid_model_content().replace("задач измерения", "задач измерения 220 В")
    provider = FakeProvider(bad, valid_model_content())
    async with await api_client(provider) as client:
        response = await client.post("/api/v1/product-cards/generate", json=product_payload)
    assert response.status_code == 200
    assert response.json()["quality"]["retry_count"] == 1

