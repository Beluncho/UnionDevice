from __future__ import annotations

from typing import Any


class AppError(Exception):
    status_code = 500
    code = "internal_error"
    public_message = "Внутренняя ошибка сервиса"

    def __init__(self, message: str | None = None, details: dict[str, Any] | None = None) -> None:
        super().__init__(message or self.public_message)
        self.details = details or {}


class ProviderConfigurationError(AppError):
    status_code = 502
    code = "provider_not_configured"
    public_message = "LLM-провайдер не настроен"


class ProviderTimeoutError(AppError):
    status_code = 504
    code = "provider_timeout"
    public_message = "LLM-провайдер не ответил вовремя"


class ProviderRequestError(AppError):
    status_code = 502
    code = "provider_error"
    public_message = "Ошибка обращения к LLM-провайдеру"


class ProviderInvalidResponseError(AppError):
    status_code = 502
    code = "provider_invalid_response"
    public_message = "LLM-провайдер вернул некорректный результат"

