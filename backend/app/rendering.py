from __future__ import annotations

from backend.app.schemas import Characteristic, DraftStatus


def render_markdown(
    *,
    status: DraftStatus,
    seo_title: str,
    seo_description: str,
    characteristics: list[Characteristic],
    search_queries: list[str],
    commercial_block: str,
    missing_fields: list[str],
) -> str:
    lines: list[str] = []
    if status is DraftStatus.NEEDS_CLARIFICATION:
        lines.extend(
            [
                "> ⚠️ Черновик требует уточнения исходных данных.",
                f"> Отсутствуют: {', '.join(missing_fields)}.",
                "",
            ]
        )
    lines.extend(
        [
            f"# {seo_title}",
            "",
            seo_description,
            "",
            "## Ключевые характеристики",
            "",
        ]
    )
    lines.extend(f"- **{item.name}:** {item.value}" for item in characteristics)
    lines.extend(["", "## Поисковые запросы", ""])
    lines.extend(f"- {item}" for item in search_queries)
    lines.extend(["", "## Для менеджера", "", commercial_block])
    return "\n".join(lines).strip() + "\n"

