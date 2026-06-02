# Управление жизненным циклом контекстных переменных
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.errors import register_error_handlers
from app.routers import analysis, health, history
from app.services.ml_service import SentimentAnalyzer

structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.dev.ConsoleRenderer(),
    ]
)

logger = structlog.get_logger()

ml_models: dict = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Логирование
    logger.info("app_starting")

    analyzer = SentimentAnalyzer(
        model_name=settings.model_name,
        max_length=settings.model_max_length,
    )
    analyzer.load()
    ml_models["analyzer"] = analyzer

    logger.info("app_ready", model=settings.model_name)
    yield

    # Graceful Shutdown
    logger.info("app_shutting_down")
    analyzer.cleanup()
    ml_models.clear()
    logger.info("app_stopped")


app = FastAPI(
    title="Sentiment Analysis API",
    description="ML-сервис для анализа тональности текста",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Обработка ошибок
register_error_handlers(app)

app.include_router(health.router)
app.include_router(analysis.router)
app.include_router(history.router)

# Graceful Shutdown: uvicorn ловит SIGTERM сам и отрабатывает lifespan-блок
# после yield (cleanup модели), корректно завершая текущие запросы.
