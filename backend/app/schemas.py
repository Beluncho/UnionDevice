from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ProductInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=200)
    manufacturer: str | None = Field(default=None, max_length=200)
    specs: dict[str, str] = Field(default_factory=dict, max_length=100)
    description: str | None = Field(default=None, max_length=20_000)

    @field_validator("manufacturer", "description", mode="before")
    @classmethod
    def blank_string_to_none(cls, value: Any) -> Any:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("specs")
    @classmethod
    def validate_specs(cls, value: dict[str, str]) -> dict[str, str]:
        normalized: dict[str, str] = {}
        for raw_key, raw_value in value.items():
            if not isinstance(raw_key, str) or not isinstance(raw_value, str):
                raise ValueError("spec keys and values must be strings")
            key = raw_key.strip()
            item = raw_value.strip()
            if not key or not item:
                raise ValueError("spec keys and values must not be blank")
            if len(key) > 500 or len(item) > 500:
                raise ValueError("spec keys and values must be at most 500 characters")
            normalized[key] = item
        return normalized

    @model_validator(mode="after")
    def require_source_facts(self) -> ProductInput:
        if not self.specs and not self.description:
            raise ValueError("at least one of specs or description is required")
        return self


class DraftStatus(StrEnum):
    DRAFT_READY = "draft_ready"
    NEEDS_CLARIFICATION = "needs_clarification"


class Characteristic(BaseModel):
    name: str
    value: str


class DraftOutput(BaseModel):
    seo_title: str
    seo_description: str
    key_characteristics: list[Characteristic]
    search_queries: list[str]
    commercial_block: str
    markdown: str


class QualityInfo(BaseModel):
    grounded: bool
    retry_count: int = Field(ge=0, le=1)


class GenerateResponse(BaseModel):
    status: DraftStatus
    draft: DraftOutput | None
    missing_fields: list[str]
    warnings: list[str]
    quality: QualityInfo
    request_id: str


class ExampleItem(BaseModel):
    id: str
    label: str
    product: ProductInput


class HealthResponse(BaseModel):
    status: str = "ok"


class ErrorBody(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)
    request_id: str


class ErrorEnvelope(BaseModel):
    error: ErrorBody

