# Асинхронная очередь задач
import structlog
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.config import settings
from app.models import AnalysisResult
from app.services.ml_service import SentimentAnalyzer
from app.workers.celery_app import celery_app

logger = structlog.get_logger()

_analyzer: SentimentAnalyzer | None = None


def get_analyzer() -> SentimentAnalyzer:
    global _analyzer
    if _analyzer is None or not _analyzer.is_ready:
        _analyzer = SentimentAnalyzer(settings.model_name, settings.model_max_length)
        _analyzer.load()
    return _analyzer


@celery_app.task(bind=True, name="analyze_sentiment")
def analyze_sentiment_task(self, text: str, confidence_threshold: float = 0.5) -> dict:
    logger.info("celery_task_started", task_id=self.request.id, text_length=len(text))

    analyzer = get_analyzer()
    result = analyzer.predict(text)

    engine = create_engine(settings.database_url_sync)
    with Session(engine) as session:
        db_record = AnalysisResult(
            text=text,
            sentiment=result["sentiment"],
            confidence=result["confidence"],
            processing_time_ms=result["processing_time_ms"],
        )
        session.add(db_record)
        session.commit()
        session.refresh(db_record)
        record_id = db_record.id
        created_at = db_record.created_at.isoformat()

    engine.dispose()

    logger.info("celery_task_complete", task_id=self.request.id, record_id=record_id)

    return {
        "id": record_id,
        "text": text,
        "sentiment": result["sentiment"],
        "confidence": result["confidence"],
        "processing_time_ms": result["processing_time_ms"],
        "created_at": created_at,
    }
