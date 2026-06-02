# История запросов
import structlog
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import AnalysisResult
from app.schemas import AnalyzeResponse, HistoryResponse

logger = structlog.get_logger()
router = APIRouter(prefix="/api", tags=["history"])


@router.get("/history", response_model=HistoryResponse)
async def get_history(
    page: int = Query(1, ge=1, description="Номер страницы"),
    per_page: int = Query(20, ge=1, le=100, description="Записей на странице"),
    db: AsyncSession = Depends(get_db),
) -> HistoryResponse:
    """Получить историю анализов с пагинацией."""
    # Логирование
    logger.info("history_request", page=page, per_page=per_page)

    total_result = await db.execute(select(func.count(AnalysisResult.id)))
    total = total_result.scalar_one()

    offset = (page - 1) * per_page
    stmt = (
        select(AnalysisResult)
        .order_by(AnalysisResult.created_at.desc())
        .offset(offset)
        .limit(per_page)
    )
    result = await db.execute(stmt)
    records = result.scalars().all()

    items = [AnalyzeResponse.model_validate(r) for r in records]

    return HistoryResponse(items=items, total=total, page=page, per_page=per_page)


@router.get("/stats")
async def get_stats(db: AsyncSession = Depends(get_db)) -> dict:
    """Статистика по анализам для дашборда."""
    total_result = await db.execute(select(func.count(AnalysisResult.id)))
    total = total_result.scalar_one()

    positive_result = await db.execute(
        select(func.count(AnalysisResult.id)).where(AnalysisResult.sentiment == "POSITIVE")
    )
    positive = positive_result.scalar_one()

    negative_result = await db.execute(
        select(func.count(AnalysisResult.id)).where(AnalysisResult.sentiment == "NEGATIVE")
    )
    negative = negative_result.scalar_one()

    avg_confidence_result = await db.execute(select(func.avg(AnalysisResult.confidence)))
    avg_confidence = avg_confidence_result.scalar_one() or 0

    avg_time_result = await db.execute(select(func.avg(AnalysisResult.processing_time_ms)))
    avg_time = avg_time_result.scalar_one() or 0

    return {
        "total_analyses": total,
        "positive_count": positive,
        "negative_count": negative,
        "avg_confidence": round(float(avg_confidence), 4),
        "avg_processing_time_ms": round(float(avg_time), 2),
    }
