from pydantic import BaseModel


class LogUploadResponse(BaseModel):
    id: int
    filename: str
    status: str
    parsed_entries: int
    message: str


class BatchLogUploadResponse(BaseModel):
    items: list[LogUploadResponse]
    uploaded_count: int
    message: str


class LogSummary(BaseModel):
    id: int
    filename: str
    status: str
    owner_email: str
    uploaded_at: str
    size_bytes: int
    parsed_entries: int
    error_count: int
    warn_count: int


class LogListResponse(BaseModel):
    items: list[LogSummary]


class LogEntryResponse(BaseModel):
    id: int
    line_number: int
    timestamp: str | None = None
    level: str | None = None
    message: str
    is_key_event: bool


class LogDetailResponse(BaseModel):
    id: int
    filename: str
    status: str
    owner_email: str
    uploaded_at: str
    size_bytes: int
    content_preview: str
    entries: list[LogEntryResponse]
    parsed_entries: int
    error_count: int
    warn_count: int
    total_parsed_entries: int
    total_error_count: int
    total_warn_count: int


class AnalyzeResponse(BaseModel):
    log_id: int
    status: str
    summary: str
    causes: str
    suggestions: str


class AnalysisRecord(BaseModel):
    id: int
    summary: str
    causes: str
    suggestions: str
    analyzed_at: str


class AnalysisHistoryResponse(BaseModel):
    items: list[AnalysisRecord]
