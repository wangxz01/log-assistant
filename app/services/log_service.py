from fastapi import UploadFile

from app.models.log import LogRecord
from app.schemas.log import AnalyzeResponse, LogDetailResponse, LogListResponse, LogSummary, LogUploadResponse


class LogService:
    def __init__(self) -> None:
        self._logs = [
            LogRecord(id=1, filename="sample.log", status="uploaded"),
            LogRecord(id=2, filename="system.log", status="analyzed"),
        ]

    async def upload(self, file: UploadFile) -> LogUploadResponse:
        new_id = len(self._logs) + 1
        record = LogRecord(id=new_id, filename=file.filename or "unknown.log", status="uploaded")
        self._logs.append(record)
        return LogUploadResponse(
            id=record.id,
            filename=record.filename,
            message="Log received. Processing is not implemented yet.",
        )

    def list_logs(self) -> LogListResponse:
        items = [LogSummary(id=log.id, filename=log.filename, status=log.status) for log in self._logs]
        return LogListResponse(items=items)

    def get_log(self, log_id: int) -> LogDetailResponse:
        log = self._find_log(log_id)
        return LogDetailResponse(
            id=log.id,
            filename=log.filename,
            status=log.status,
            content_preview="Placeholder preview for uploaded log content.",
        )

    def analyze(self, log_id: int) -> AnalyzeResponse:
        log = self._find_log(log_id)
        log.status = "analysis_requested"
        return AnalyzeResponse(
            log_id=log.id,
            status=log.status,
            summary="Analysis has been queued. Insight generation is not implemented yet.",
        )

    def _find_log(self, log_id: int) -> LogRecord:
        for log in self._logs:
            if log.id == log_id:
                return log
        return LogRecord(id=log_id, filename="unknown.log", status="not_found")


log_service = LogService()

