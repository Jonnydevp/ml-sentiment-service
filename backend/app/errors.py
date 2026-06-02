# Обработка ошибок
import structlog
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

logger = structlog.get_logger()


class MLModelError(Exception):
    def __init__(self, message: str = "Ошибка при работе модели"):
        self.message = message


class MLModelNotReadyError(Exception):
    def __init__(self, message: str = "ML-модель ещё не загружена"):
        self.message = message


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(MLModelError)
    async def ml_model_error_handler(request: Request, exc: MLModelError) -> JSONResponse:
        logger.error("ml_model_error", detail=exc.message, path=str(request.url))
        return JSONResponse(
            status_code=500,
            content={"detail": exc.message, "error_code": "ML_ERROR"},
        )

    @app.exception_handler(MLModelNotReadyError)
    async def ml_not_ready_handler(request: Request, exc: MLModelNotReadyError) -> JSONResponse:
        logger.warning("ml_model_not_ready", detail=exc.message)
        return JSONResponse(
            status_code=503,
            content={"detail": exc.message, "error_code": "MODEL_NOT_READY"},
        )

    @app.exception_handler(ValidationError)
    async def validation_error_handler(request: Request, exc: ValidationError) -> JSONResponse:
        logger.warning("validation_error", errors=str(exc.errors()))
        return JSONResponse(
            status_code=422,
            content={"detail": str(exc.errors()), "error_code": "VALIDATION_ERROR"},
        )

    @app.exception_handler(Exception)
    async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.error("unhandled_error", error=str(exc), path=str(request.url))
        return JSONResponse(
            status_code=500,
            content={"detail": "Внутренняя ошибка сервера", "error_code": "INTERNAL_ERROR"},
        )
