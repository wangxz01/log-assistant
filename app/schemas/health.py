from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    ai_configured: bool = False
    redis_ok: bool = True
