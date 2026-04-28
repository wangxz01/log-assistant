from fastapi import APIRouter, Depends, File, Query, UploadFile, status

from app.api.dependencies import get_current_user
from app.models.user import User
from app.schemas.log import (
    AnalysisHistoryResponse,
    AnalyzeResponse,
    AnalyzeStatusResponse,
    BatchLogUploadResponse,
    LogDetailResponse,
    LogListResponse,
    LogUploadResponse,
    StatsResponse,
)
from app.services.log_service import log_service


router = APIRouter()


@router.post("/upload", response_model=LogUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_log(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
) -> LogUploadResponse:
    return await log_service.upload(file, current_user)


@router.post("/upload/batch", response_model=BatchLogUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_logs(
    files: list[UploadFile] = File(...),
    current_user: User = Depends(get_current_user),
) -> BatchLogUploadResponse:
    return await log_service.upload_many(files, current_user)


@router.get("", response_model=LogListResponse)
def list_logs(
    keyword: str | None = Query(default=None),
    level: str | None = Query(default=None),
    log_status: str | None = Query(default=None, alias="status"),
    service: str | None = Query(default=None),
    start_time: str | None = Query(default=None),
    end_time: str | None = Query(default=None),
    current_user: User = Depends(get_current_user),
) -> LogListResponse:
    return log_service.list_logs(current_user, keyword, level, log_status, service, start_time, end_time)


@router.get("/{log_id}", response_model=LogDetailResponse)
def get_log(
    log_id: int,
    keyword: str | None = Query(default=None),
    level: str | None = Query(default=None),
    service: str | None = Query(default=None),
    start_time: str | None = Query(default=None),
    end_time: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
) -> LogDetailResponse:
    return log_service.get_log(log_id, current_user, keyword, level, service, start_time, end_time, page, per_page)


@router.post("/{log_id}/analyze", response_model=AnalyzeResponse)
def analyze_log(
    log_id: int,
    current_user: User = Depends(get_current_user),
) -> AnalyzeResponse:
    return log_service.analyze(log_id, current_user)


@router.get("/{log_id}/analyze/status", response_model=AnalyzeStatusResponse)
def get_analyze_status(
    log_id: int,
    current_user: User = Depends(get_current_user),
) -> AnalyzeStatusResponse:
    return log_service.get_analyze_status(log_id, current_user)


@router.get("/{log_id}/analyses", response_model=AnalysisHistoryResponse)
def list_analyses(
    log_id: int,
    current_user: User = Depends(get_current_user),
) -> AnalysisHistoryResponse:
    return log_service.list_analyses(log_id, current_user)


@router.get("/{log_id}/stats", response_model=StatsResponse)
def get_log_stats(
    log_id: int,
    current_user: User = Depends(get_current_user),
) -> StatsResponse:
    return log_service.get_stats(log_id, current_user)
