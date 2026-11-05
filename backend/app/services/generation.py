from __future__ import annotations

from backend.app.errors import ProviderInvalidResponseError
from backend.app.prompting import correction_messages, initial_messages
from backend.app.providers.base import LLMProvider
from backend.app.rendering import render_markdown
from backend.app.schemas import (
    Characteristic,
    DraftOutput,
    DraftStatus,
    GenerateResponse,
    ProductInput,
    QualityInfo,
)
from backend.app.validation import ValidatedModelDraft, validate_model_content


class ProductCardService:
    def __init__(self, provider: LLMProvider) -> None:
        self._provider = provider

    async def generate(self, product: ProductInput, request_id: str) -> GenerateResponse:
        missing_fields = self._missing_fields(product)
        status = (
            DraftStatus.NEEDS_CLARIFICATION
            if missing_fields
            else DraftStatus.DRAFT_READY
        )
        warnings = (
            ["Проверьте и дополните отсутствующие данные перед публикацией"]
            if missing_fields
            else []
        )

        first = await self._provider.generate(initial_messages(product))
        validated, violations = validate_model_content(first.content, product)
        retry_count = 0
        if validated is None:
            retry_count = 1
            second = await self._provider.generate(
                correction_messages(product, first.content, violations)
            )
            validated, violations = validate_model_content(second.content, product)
        if validated is None:
            if status is DraftStatus.NEEDS_CLARIFICATION:
                return GenerateResponse(
                    status=status,
                    draft=None,
                    missing_fields=missing_fields,
                    warnings=[
                        "LLM не смогла сформировать проверенный черновик по неполным данным",
                        "Дополните отсутствующие поля и повторите генерацию",
                    ],
                    quality=QualityInfo(grounded=False, retry_count=retry_count),
                    request_id=request_id,
                )
            raise ProviderInvalidResponseError(details={"violation_count": len(violations)})

        characteristics = self._characteristics(product, validated)
        markdown = render_markdown(
            status=status,
            seo_title=validated.seo_title,
            seo_description=validated.seo_description,
            characteristics=characteristics,
            search_queries=validated.search_queries,
            commercial_block=validated.commercial_block,
            missing_fields=missing_fields,
        )
        return GenerateResponse(
            status=status,
            draft=DraftOutput(
                seo_title=validated.seo_title,
                seo_description=validated.seo_description,
                key_characteristics=characteristics,
                search_queries=validated.search_queries,
                commercial_block=validated.commercial_block,
                markdown=markdown,
            ),
            missing_fields=missing_fields,
            warnings=warnings,
            quality=QualityInfo(grounded=True, retry_count=retry_count),
            request_id=request_id,
        )

    @staticmethod
    def _missing_fields(product: ProductInput) -> list[str]:
        missing: list[str] = []
        if not product.manufacturer:
            missing.append("manufacturer")
        if not product.specs:
            missing.append("specs")
        if not product.description:
            missing.append("description")
        return missing

    @staticmethod
    def _characteristics(
        product: ProductInput,
        validated: ValidatedModelDraft,
    ) -> list[Characteristic]:
        if not product.specs:
            return [Characteristic(name="Характеристики", value="Данных нет")]
        return [
            Characteristic(name=name, value=product.specs[name])
            for name in validated.key_characteristic_names
        ]

