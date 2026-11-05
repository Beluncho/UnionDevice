from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from typing import Any

from backend.app.schemas import ProductInput


@dataclass(frozen=True, slots=True)
class ValidatedModelDraft:
    seo_title: str
    seo_description: str
    key_characteristic_names: list[str]
    search_queries: list[str]
    commercial_block: str


_TECHNICAL_TOKEN = re.compile(
    r"(?iu)(?<!\w)(?:"
    r"[a-zа-я]{1,12}[-/]?\d+[a-zа-я0-9./+%-]*|"
    r"\d+(?:[.,]\d+)?\s*(?:°[cс]|мпа|кпа|гпа|па|мбар|бар|"
    r"кгц|мгц|гц|ма|а|в|мм|см|м|кг|г|ч|с|%)"
    r")(?!\w)"
)


def _normalize(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).lower().replace("ё", "е")
    value = value.replace("−", "-").replace("–", "-").replace("—", "-")
    value = value.replace(",", ".")
    return re.sub(r"\s+", "", value)


def _extract_json(content: str) -> dict[str, Any]:
    start = content.find("{")
    end = content.rfind("}")
    if start == -1 or end <= start:
        raise ValueError("Ответ не содержит JSON-объект")
    parsed = json.loads(content[start : end + 1])
    if not isinstance(parsed, dict):
        raise ValueError("Корневое значение должно быть JSON-объектом")
    return parsed


def _required_string(data: dict[str, Any], field: str) -> str:
    value = data.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field}: требуется непустая строка")
    return value.strip()


def _grounding_violations(product: ProductInput, generated_text: str) -> list[str]:
    source = "\n".join(
        [
            product.name,
            product.manufacturer or "",
            *(f"{key} {value}" for key, value in product.specs.items()),
            product.description or "",
        ]
    )
    normalized_source = _normalize(source)
    missing: list[str] = []
    for match in _TECHNICAL_TOKEN.finditer(generated_text):
        token = match.group(0).strip()
        if token.lower() == "b2b":
            continue
        if _normalize(token) not in normalized_source and token not in missing:
            missing.append(token)
    return missing


def validate_model_content(
    content: str,
    product: ProductInput,
) -> tuple[ValidatedModelDraft | None, list[str]]:
    violations: list[str] = []
    try:
        data = _extract_json(content)
    except (ValueError, json.JSONDecodeError) as exc:
        return None, [str(exc)]

    try:
        seo_title = _required_string(data, "seo_title")
        seo_description = _required_string(data, "seo_description")
        commercial_block = _required_string(data, "commercial_block")
    except ValueError as exc:
        return None, [str(exc)]

    if len(seo_title) > 70:
        violations.append(f"seo_title длиннее 70 символов: {len(seo_title)}")
    if not 800 <= len(seo_description) <= 1200:
        violations.append(
            f"seo_description должен содержать 800–1200 символов: {len(seo_description)}"
        )

    raw_queries = data.get("search_queries")
    if not isinstance(raw_queries, list) or not all(
        isinstance(item, str) and item.strip() for item in raw_queries
    ):
        queries: list[str] = []
        violations.append("search_queries должен быть массивом непустых строк")
    else:
        queries = [item.strip() for item in raw_queries]
        if not 3 <= len(queries) <= 5:
            violations.append("search_queries должен содержать 3–5 элементов")
        if len({_normalize(item) for item in queries}) != len(queries):
            violations.append("search_queries должен содержать уникальные элементы")

    raw_keys = data.get("key_characteristic_names")
    if not isinstance(raw_keys, list) or not all(isinstance(item, str) for item in raw_keys):
        characteristic_names: list[str] = []
        violations.append("key_characteristic_names должен быть массивом строк")
    else:
        characteristic_names = [item.strip() for item in raw_keys if item.strip()]
        unknown = [item for item in characteristic_names if item not in product.specs]
        if unknown:
            violations.append("Неизвестные ключи характеристик: " + ", ".join(unknown))
        if product.specs and not characteristic_names:
            violations.append("Нужно выбрать хотя бы одну характеристику из specs")
        if len(characteristic_names) > 10:
            violations.append("Можно выбрать не более 10 характеристик")

    generated = "\n".join([seo_title, seo_description, commercial_block, *queries])
    ungrounded = _grounding_violations(product, generated)
    if ungrounded:
        violations.append("Технические значения отсутствуют во входе: " + ", ".join(ungrounded))

    if violations:
        return None, violations
    return (
        ValidatedModelDraft(
            seo_title=seo_title,
            seo_description=seo_description,
            key_characteristic_names=characteristic_names,
            search_queries=queries,
            commercial_block=commercial_block,
        ),
        [],
    )

