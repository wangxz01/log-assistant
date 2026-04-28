from fastapi import APIRouter

from app.core.config import settings
from app.schemas.health import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    redis_ok = False
    try:
        import redis

        r = redis.Redis.from_url(settings.redis_url, decode_responses=True)
        r.ping()
        redis_ok = True
    except Exception:
        pass

    return HealthResponse(
        status="ok",
        ai_configured=bool(settings.deepseek_api_key),
        redis_ok=redis_ok,
    )
