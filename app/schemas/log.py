from pydantic import BaseModel


class LogUploadResponse(BaseModel):
    id: int
    filename: str
    status: str
    parsed_entries: int
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


class AnalyzeResponse(BaseModel):
    log_id: int
    status: str
    summary: str
    parsed_entries: int
    error_count: int
    warn_count: int
