# Анализ тональности — основной роутер
import time

import structlog
from celery.result import AsyncResult
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.errors import MLModelNotReadyError
from app.models import AnalysisResult
from app.schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    AsyncTaskResponse,
    BatchAnalyzeRequest,
    TaskStatusResponse,
)
from app.workers.celery_app import celery_app
from app.workers.tasks import analyze_sentiment_task

logger = structlog.get_logger()
router = APIRouter(prefix="/api", tags=["analysis"])


@router.post("/analyze", response_model=AnalyzeResponse, status_code=200)
async def analyze_text(
    request: AnalyzeRequest,
    db: AsyncSession = Depends(get_db),
) -> AnalyzeResponse:
    """Синхронный анализ тональности текста."""
    from app.main import ml_models

    analyzer = ml_models.get("analyzer")
    if not analyzer or not analyzer.is_ready:
        raise MLModelNotReadyError()

    # Логирование
    logger.info("analyze_request", text_length=len(request.text))
    start = time.time()

    result = analyzer.predict(request.text)

    db_record = AnalysisResult(
        text=request.text,
        sentiment=result["sentiment"],
        confidence=result["confidence"],
        processing_time_ms=result["processing_time_ms"],
    )
    db.add(db_record)
    await db.flush()
    await db.refresh(db_record)

    total_ms = (time.time() - start) * 1000
    logger.info("analyze_complete", record_id=db_record.id, total_ms=round(total_ms, 2))

    return AnalyzeResponse.model_validate(db_record)


# Асинхронная очередь задач
@router.post("/analyze/async", response_model=AsyncTaskResponse, status_code=202)
async def analyze_text_async(request: AnalyzeRequest) -> AsyncTaskResponse:
    """Асинхронный анализ через Celery. Возвращает task_id для polling."""
    logger.info("async_analyze_request", text_length=len(request.text))

    task = analyze_sentiment_task.delay(request.text, request.confidence_threshold)

    return AsyncTaskResponse(
        task_id=task.id,
        status="PENDING",
        message="Задача принята в обработку",
    )


@router.get("/task/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str) -> TaskStatusResponse:
    """Проверка статуса асинхронной задачи (polling)."""
    result = AsyncResult(task_id, app=celery_app)

    if result.state == "PENDING":
        return TaskStatusResponse(task_id=task_id, status="PENDING")
    elif result.state == "STARTED":
        return TaskStatusResponse(task_id=task_id, status="PROCESSING")
    elif result.state == "SUCCESS":
        data = result.result
        return TaskStatusResponse(
            task_id=task_id,
            status="SUCCESS",
            result=AnalyzeResponse(**data),
        )
    elif result.state == "FAILURE":
        return TaskStatusResponse(
            task_id=task_id,
            status="FAILURE",
            error=str(result.result),
        )
    else:
        return TaskStatusResponse(task_id=task_id, status=result.state)


@router.post("/analyze/batch", response_model=list[AnalyzeResponse], status_code=200)
async def analyze_batch(
    request: BatchAnalyzeRequest,
    db: AsyncSession = Depends(get_db),
) -> list[AnalyzeResponse]:
    """Батч-анализ нескольких текстов за один запрос."""
    from app.main import ml_models

    analyzer = ml_models.get("analyzer")
    if not analyzer or not analyzer.is_ready:
        raise MLModelNotReadyError()

    # Управление ресурсами — батчинг
    results = analyzer.predict_batch(request.texts)

    records = [
        AnalysisResult(
            text=text_input,
            sentiment=result["sentiment"],
            confidence=result["confidence"],
            processing_time_ms=result["processing_time_ms"],
        )
        for text_input, result in zip(request.texts, results)
    ]
    db.add_all(records)
    await db.flush()
    for record in records:
        await db.refresh(record)

    logger.info("batch_analyze_complete", count=len(records))
    return [AnalyzeResponse.model_validate(r) for r in records]
