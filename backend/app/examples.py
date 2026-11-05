from __future__ import annotations

import json
from pathlib import Path

from backend.app.schemas import ExampleItem, ProductInput

_LABELS = {
    "testo-510": "testo 510 — полный пример",
    "testo-830-t1": "testo 830-T1 — полный пример",
    "testo-510.partial": "testo 510 — недостаточно данных",
}


def default_examples_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "examples" / "inputs"


def load_examples(directory: Path | None = None) -> list[ExampleItem]:
    source = directory or default_examples_dir()
    if not source.exists():
        return []
    result: list[ExampleItem] = []
    for path in sorted(source.glob("*.json")):
        product = ProductInput.model_validate(json.loads(path.read_text(encoding="utf-8")))
        result.append(
            ExampleItem(
                id=path.stem,
                label=_LABELS.get(path.stem, path.stem),
                product=product,
            )
        )
    return result

