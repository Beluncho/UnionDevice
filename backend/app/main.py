from __future__ import annotations

import logging
import time
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.config import Settings, get_settings
from backend.app.errors import AppError
from backend.app.examples import load_examples
from backend.app.providers import LLMProvider, OpenAICompatibleProvider
from backend.app.schemas import (
    ErrorBody,
    ErrorEnvelope,
    ExampleItem,
    GenerateResponse,
    HealthResponse,
    ProductInput,
)
from backend.app.services import ProductCardService

logger = logging.getLogger("product_card_api")


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", str(uuid.uuid4()))


def _error_response(
    request: Request,
    *,
    status_code: int,
    code: str,
    message: str,
    details: dict | None = None,
) -> JSONResponse:
    payload = ErrorEnvelope(
        error=ErrorBody(
            code=code,
            message=message,
            details=details or {},
            request_id=_request_id(request),
        )
    )
    return JSONResponse(status_code=status_code, content=payload.model_dump(mode="json"))


def create_app(
    *,
    provider: LLMProvider | None = None,
    settings: Settings | None = None,
) -> FastAPI:
    active_settings = settings or get_settings()
    active_provider = provider or OpenAICompatibleProvider(active_settings)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        close = getattr(active_provider, "aclose", None)
        if close is not None:
            await close()

    app = FastAPI(
        title="AI-помощник товарных карточек",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.state.card_service = ProductCardService(active_provider)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=active_settings.cors_origin_list,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "X-Request-ID"],
    )

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        request.state.request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        started = time.perf_counter()
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        if request.url.path != "/api/v1/health" or response.status_code >= 400:
            logger.info(
                "request_completed method=%s path=%s status=%s duration_ms=%d "
                "error_code=%s request_id=%s",
                request.method,
                request.url.path,
                response.status_code,
                int((time.perf_counter() - started) * 1000),
                getattr(request.state, "error_code", "none"),
                request.state.request_id,
            )
        return response

    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        request.state.error_code = exc.code
        return _error_response(
            request,
            status_code=exc.status_code,
            code=exc.code,
            message=exc.public_message,
            details=exc.details,
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        errors = exc.errors()
        insufficient = any(
            "at least one of specs or description is required" in str(item.get("ctx", {}))
            for item in errors
        )
        request.state.error_code = (
            "insufficient_product_data" if insufficient else "validation_error"
        )
        return _error_response(
            request,
            status_code=422,
            code="insufficient_product_data" if insufficient else "validation_error",
            message=(
                "Недостаточно данных для генерации черновика"
                if insufficient
                else "Некорректные входные данные"
            ),
            details={
                "errors": [
                    {
                        "location": [str(part) for part in item.get("loc", ())],
                        "message": item.get("msg", "Invalid value"),
                        "type": item.get("type", "value_error"),
                    }
                    for item in errors
                ]
            },
        )

    @app.get("/api/v1/health", response_model=HealthResponse, tags=["system"])
    async def health() -> HealthResponse:
        return HealthResponse()

    @app.get("/api/v1/examples", response_model=list[ExampleItem], tags=["examples"])
    async def examples() -> list[ExampleItem]:
        return load_examples()

    @app.post(
        "/api/v1/product-cards/generate",
        response_model=GenerateResponse,
        responses={
            422: {"model": ErrorEnvelope},
            502: {"model": ErrorEnvelope},
            504: {"model": ErrorEnvelope},
        },
        tags=["product cards"],
    )
    async def generate(product: ProductInput, request: Request) -> GenerateResponse:
        service: ProductCardService = request.app.state.card_service
        return await service.generate(product, _request_id(request))

    return app


app = create_app()

