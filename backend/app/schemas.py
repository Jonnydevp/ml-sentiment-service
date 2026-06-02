# Валидация данных
from datetime import datetime

from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    text: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="Текст для анализа тональности",
        examples=["I love this product! It works great."],
    )
    confidence_threshold: float = Field(
        0.5,
        ge=0.0,
        le=1.0,
        description="Минимальный порог уверенности модели (0.0–1.0)",
    )


class AnalyzeResponse(BaseModel):
    id: int
    text: str
    sentiment: str = Field(..., description="Результат: POSITIVE / NEGATIVE")
    confidence: float = Field(..., description="Уверенность модели (0.0–1.0)")
    processing_time_ms: float = Field(..., description="Время обработки в миллисекундах")
    created_at: datetime

    model_config = {"from_attributes": True}


class AsyncTaskResponse(BaseModel):
    task_id: str = Field(..., description="ID асинхронной задачи")
    status: str = Field("PENDING", description="Статус: PENDING / PROCESSING / SUCCESS / FAILURE")
    message: str = Field("Задача принята в обработку")


class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    result: AnalyzeResponse | None = None
    error: str | None = None


class HealthResponse(BaseModel):
    status: str
    db: str
    redis: str
    model: str


class ErrorResponse(BaseModel):
    detail: str
    error_code: str | None = None


class HistoryResponse(BaseModel):
    items: list[AnalyzeResponse]
    total: int
    page: int
    per_page: int


class BatchAnalyzeRequest(BaseModel):
    texts: list[str] = Field(
        ...,
        min_length=1,
        max_length=10,
        description="Список текстов для анализа (макс. 10)",
    )
    confidence_threshold: float = Field(0.5, ge=0.0, le=1.0)
