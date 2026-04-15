from fastapi import FastAPI

from app.api.router import api_router
from app.core.config import settings


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Minimal backend scaffold for an intelligent log analysis assistant.",
)

app.include_router(api_router)

