# Health Check
import redis.asyncio as aioredis
import structlog
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db

logger = structlog.get_logger()
router = APIRouter(tags=["health"])


@router.get("/api/health")
async def health_check(db: AsyncSession = Depends(get_db)) -> dict:
    health = {"status": "healthy", "db": "unknown", "redis": "unknown", "model": "unknown"}

    try:
        await db.execute(text("SELECT 1"))
        health["db"] = "ok"
    except Exception as e:
        health["db"] = f"error: {e}"
        health["status"] = "unhealthy"
        logger.error("health_db_fail", error=str(e))

    try:
        r = aioredis.from_url(f"redis://{settings.redis_host}:{settings.redis_port}")
        await r.ping()
        await r.aclose()
        health["redis"] = "ok"
    except Exception as e:
        health["redis"] = f"error: {e}"
        health["status"] = "unhealthy"
        logger.error("health_redis_fail", error=str(e))

    from app.main import ml_models
    if ml_models.get("analyzer") and ml_models["analyzer"].is_ready:
        health["model"] = "ok"
    else:
        health["model"] = "not_loaded"
        health["status"] = "unhealthy"

    status_code = 200 if health["status"] == "healthy" else 503
    from fastapi.responses import JSONResponse
    return JSONResponse(content=health, status_code=status_code)
