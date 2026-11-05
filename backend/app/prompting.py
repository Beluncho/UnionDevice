from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from backend.app.schemas import ProductInput


@lru_cache
def system_prompt() -> str:
    path = Path(__file__).with_name("prompts") / "product_card_system.md"
    return path.read_text(encoding="utf-8").strip()


def initial_messages(product: ProductInput) -> list[dict[str, str]]:
    payload = product.model_dump(mode="json")
    user_prompt = (
        "Сформируй черновик по данным ниже.\n"
        f"ALLOWED_SPEC_KEYS={json.dumps(list(product.specs), ensure_ascii=False)}\n"
        "<PRODUCT_JSON>\n"
        f"{json.dumps(payload, ensure_ascii=False, indent=2)}\n"
        "</PRODUCT_JSON>"
    )
    return [
        {"role": "system", "content": system_prompt()},
        {"role": "user", "content": user_prompt},
    ]


def correction_messages(
    product: ProductInput,
    previous_content: str,
    violations: list[str],
) -> list[dict[str, str]]:
    messages = initial_messages(product)
    messages.append({"role": "assistant", "content": previous_content[:20_000]})
    messages.append(
        {
            "role": "user",
            "content": (
                "Исправь JSON и верни только исправленный объект. Нарушения:\n- "
                + "\n- ".join(violations)
            ),
        }
    )
    return messages

