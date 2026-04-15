from pydantic import BaseModel


class LogUploadResponse(BaseModel):
    id: int
    filename: str
    message: str


class LogSummary(BaseModel):
    id: int
    filename: str
    status: str


class LogListResponse(BaseModel):
    items: list[LogSummary]


class LogDetailResponse(BaseModel):
    id: int
    filename: str
    status: str
    content_preview: str


class AnalyzeResponse(BaseModel):
    log_id: int
    status: str
    summary: str

