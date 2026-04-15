from fastapi import APIRouter, File, UploadFile, status

from app.schemas.log import AnalyzeResponse, LogDetailResponse, LogListResponse, LogUploadResponse
from app.services.log_service import log_service


router = APIRouter()


@router.post("/upload", response_model=LogUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_log(file: UploadFile = File(...)) -> LogUploadResponse:
    return await log_service.upload(file)


@router.get("", response_model=LogListResponse)
def list_logs() -> LogListResponse:
    return log_service.list_logs()


@router.get("/{log_id}", response_model=LogDetailResponse)
def get_log(log_id: int) -> LogDetailResponse:
    return log_service.get_log(log_id)


@router.post("/{log_id}/analyze", response_model=AnalyzeResponse)
def analyze_log(log_id: int) -> AnalyzeResponse:
    return log_service.analyze(log_id)

