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
    total: int = 0
    page: int = 1
    per_page: int = 20
    total_pages: int = 1


class LogEntryResponse(BaseModel):
    id: int
    line_number: int
    timestamp: str | None = None
    level: str | None = None
    service_name: str | None = None
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
    total_entries: int
    page: int
    per_page: int
    total_pages: int


class AnalyzeResponse(BaseModel):
    log_id: int
    task_id: str
    status: str


class AnalyzeStatusResponse(BaseModel):
    task_id: str
    status: str
    summary: str | None = None
    causes: list[str] | None = None
    suggestions: list[str] | None = None
    error: str | None = None


class AnalysisRecord(BaseModel):
    id: int
    summary: str
    causes: list[str]
    suggestions: list[str]
    analyzed_at: str


class AnalysisHistoryResponse(BaseModel):
    items: list[AnalysisRecord]


class AlertRuleCreate(BaseModel):
    name: str
    condition_level: str | None = None
    condition_keyword: str | None = None
    condition_service: str | None = None
    threshold: int = 1
    enabled: bool = True


class AlertRule(BaseModel):
    id: int
    name: str
    condition_level: str | None = None
    condition_keyword: str | None = None
    condition_service: str | None = None
    threshold: int
    enabled: bool
    created_at: str


class AlertRuleListResponse(BaseModel):
    items: list[AlertRule]


class AlertRuleEval(BaseModel):
    rule_id: int
    rule_name: str
    triggered: bool
    message: str


class AlertEvalResponse(BaseModel):
    alerts: list[AlertRuleEval]


class LevelDistribution(BaseModel):
    level: str
    count: int


class LevelTrendPoint(BaseModel):
    time_bucket: str
    level: str
    count: int


class ServiceDistribution(BaseModel):
    service: str
    count: int


class StatsResponse(BaseModel):
    level_distribution: list[LevelDistribution]
    level_trend: list[LevelTrendPoint]
    service_distribution: list[ServiceDistribution]
