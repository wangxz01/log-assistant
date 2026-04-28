import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import HTTPException, UploadFile, status

from app.core.config import settings
from app.core.database import get_connection, initialize_database
from app.models.user import User
from app.schemas.log import (
    AnalyzeResponse,
    BatchLogUploadResponse,
    LogDetailResponse,
    LogEntryResponse,
    LogListResponse,
    LogSummary,
    LogUploadResponse,
)


TIMESTAMP_PATTERN = re.compile(
    r"(?P<timestamp>"
    r"\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:[.,]\d+)?(?:Z|[+-]\d{2}:?\d{2})?"
    r"|[A-Z][a-z]{2}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}"
    r")"
)
LEVEL_PATTERN = re.compile(r"\b(?P<level>TRACE|DEBUG|INFO|WARN|WARNING|ERROR|FATAL|CRITICAL)\b", re.IGNORECASE)
KEY_LEVELS = {"WARN", "WARNING", "ERROR", "FATAL", "CRITICAL"}


class LogService:
    async def upload(self, file: UploadFile, user: User) -> LogUploadResponse:
        initialize_database()

        file_bytes = await file.read()
        original_filename = Path(file.filename or "uploaded.log").name
        stored_filename = f"{uuid.uuid4().hex}_{original_filename}"
        upload_dir = Path(settings.upload_dir)
        upload_dir.mkdir(parents=True, exist_ok=True)
        storage_path = upload_dir / stored_filename
        storage_path.write_bytes(file_bytes)

        entries = parse_log_entries(file_bytes.decode("utf-8", errors="replace"))

        with get_connection() as connection:
            row = connection.execute(
                """
                INSERT INTO logs (
                    user_id,
                    original_filename,
                    stored_filename,
                    storage_path,
                    content_type,
                    size_bytes,
                    status
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    user.id,
                    original_filename,
                    stored_filename,
                    str(storage_path),
                    file.content_type,
                    len(file_bytes),
                    "parsed",
                ),
            ).fetchone()
            log_id = row["id"]

            for entry in entries:
                connection.execute(
                    """
                    INSERT INTO log_entries (
                        log_id,
                        line_number,
                        event_time,
                        timestamp_text,
                        level,
                        message,
                        is_key_event
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        log_id,
                        entry["line_number"],
                        entry["event_time"],
                        entry["timestamp_text"],
                        entry["level"],
                        entry["message"],
                        entry["is_key_event"],
                    ),
                )

        return LogUploadResponse(
            id=log_id,
            filename=original_filename,
            status="parsed",
            parsed_entries=len(entries),
            message="Log uploaded and parsed.",
        )

    async def upload_many(self, files: list[UploadFile], user: User) -> BatchLogUploadResponse:
        if not files:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="At least one file is required.")

        uploaded_logs = []

        for file in files:
            uploaded_logs.append(await self.upload(file, user))

        return BatchLogUploadResponse(
            items=uploaded_logs,
            uploaded_count=len(uploaded_logs),
            message=f"Uploaded and parsed {len(uploaded_logs)} log files.",
        )

    def list_logs(
        self,
        user: User,
        keyword: str | None = None,
        level: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
    ) -> LogListResponse:
        initialize_database()
        where_clauses, params = self._build_log_filters(user, keyword, level, start_time, end_time)

        with get_connection() as connection:
            rows = connection.execute(
                f"""
                SELECT
                    l.id,
                    l.original_filename,
                    l.status,
                    l.uploaded_at,
                    l.size_bytes,
                    u.email AS owner_email,
                    (SELECT COUNT(*) FROM log_entries e WHERE e.log_id = l.id) AS parsed_entries,
                    (
                        SELECT COUNT(*)
                        FROM log_entries e
                        WHERE e.log_id = l.id AND e.level IN ('ERROR', 'FATAL', 'CRITICAL')
                    ) AS error_count,
                    (
                        SELECT COUNT(*)
                        FROM log_entries e
                        WHERE e.log_id = l.id AND e.level IN ('WARN', 'WARNING')
                    ) AS warn_count
                FROM logs l
                JOIN users u ON u.id = l.user_id
                WHERE {" AND ".join(where_clauses)}
                ORDER BY l.uploaded_at DESC, l.id DESC
                """,
                tuple(params),
            ).fetchall()

        return LogListResponse(items=[self._row_to_summary(row) for row in rows])

    def get_log(
        self,
        log_id: int,
        user: User,
        keyword: str | None = None,
        level: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
    ) -> LogDetailResponse:
        initialize_database()
        log = self._get_log_row(log_id, user)
        entries = self._get_entry_rows(log_id, keyword, level, start_time, end_time)
        stats = self._get_log_stats(log_id)

        return LogDetailResponse(
            id=log["id"],
            filename=log["original_filename"],
            status=log["status"],
            owner_email=log["owner_email"],
            uploaded_at=_format_datetime(log["uploaded_at"]),
            size_bytes=log["size_bytes"],
            content_preview=self._read_preview(log["storage_path"]),
            entries=[self._row_to_entry(row) for row in entries],
            parsed_entries=stats["parsed_entries"],
            error_count=stats["error_count"],
            warn_count=stats["warn_count"],
        )

    def analyze(self, log_id: int, user: User) -> AnalyzeResponse:
        initialize_database()
        self._get_log_row(log_id, user)
        stats = self._get_log_stats(log_id)

        with get_connection() as connection:
            connection.execute(
                "UPDATE logs SET status = %s WHERE id = %s AND user_id = %s",
                ("analyzed", log_id, user.id),
            )

        return AnalyzeResponse(
            log_id=log_id,
            status="analyzed",
            summary=(
                f"Parsed {stats['parsed_entries']} lines. "
                f"Found {stats['error_count']} error events and {stats['warn_count']} warning events."
            ),
            parsed_entries=stats["parsed_entries"],
            error_count=stats["error_count"],
            warn_count=stats["warn_count"],
        )

    def _get_log_row(self, log_id: int, user: User) -> dict[str, Any]:
        with get_connection() as connection:
            row = connection.execute(
                """
                SELECT
                    l.id,
                    l.original_filename,
                    l.status,
                    l.uploaded_at,
                    l.size_bytes,
                    l.storage_path,
                    u.email AS owner_email
                FROM logs l
                JOIN users u ON u.id = l.user_id
                WHERE l.id = %s AND l.user_id = %s
                """,
                (log_id, user.id),
            ).fetchone()

        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Log not found.")

        return row

    def _get_entry_rows(
        self,
        log_id: int,
        keyword: str | None = None,
        level: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
    ) -> list[dict[str, Any]]:
        where_clauses = ["log_id = %s"]
        params: list[Any] = [log_id]

        if keyword:
            where_clauses.append("message ILIKE %s")
            params.append(f"%{keyword}%")

        if level:
            where_clauses.append("level = %s")
            params.append(_normalize_level(level))

        parsed_start = _parse_filter_time(start_time, "start_time")
        if parsed_start:
            where_clauses.append("event_time >= %s")
            params.append(parsed_start)

        parsed_end = _parse_filter_time(end_time, "end_time")
        if parsed_end:
            where_clauses.append("event_time <= %s")
            params.append(parsed_end)

        with get_connection() as connection:
            return connection.execute(
                f"""
                SELECT id, line_number, timestamp_text, level, message, is_key_event
                FROM log_entries
                WHERE {" AND ".join(where_clauses)}
                ORDER BY line_number ASC
                LIMIT 500
                """,
                tuple(params),
            ).fetchall()

    def _get_log_stats(self, log_id: int) -> dict[str, int]:
        with get_connection() as connection:
            row = connection.execute(
                """
                SELECT
                    COUNT(*) AS parsed_entries,
                    COUNT(*) FILTER (WHERE level IN ('ERROR', 'FATAL', 'CRITICAL')) AS error_count,
                    COUNT(*) FILTER (WHERE level IN ('WARN', 'WARNING')) AS warn_count
                FROM log_entries
                WHERE log_id = %s
                """,
                (log_id,),
            ).fetchone()

        return {
            "parsed_entries": row["parsed_entries"] or 0,
            "error_count": row["error_count"] or 0,
            "warn_count": row["warn_count"] or 0,
        }

    def _build_log_filters(
        self,
        user: User,
        keyword: str | None,
        level: str | None,
        start_time: str | None,
        end_time: str | None,
    ) -> tuple[list[str], list[Any]]:
        where_clauses = ["l.user_id = %s"]
        params: list[Any] = [user.id]

        if keyword:
            where_clauses.append(
                """
                (
                    l.original_filename ILIKE %s
                    OR EXISTS (
                        SELECT 1 FROM log_entries e
                        WHERE e.log_id = l.id AND e.message ILIKE %s
                    )
                )
                """
            )
            params.extend([f"%{keyword}%", f"%{keyword}%"])

        if level:
            where_clauses.append(
                """
                EXISTS (
                    SELECT 1 FROM log_entries e
                    WHERE e.log_id = l.id AND e.level = %s
                )
                """
            )
            params.append(_normalize_level(level))

        parsed_start = _parse_filter_time(start_time, "start_time")
        if parsed_start:
            where_clauses.append(
                """
                EXISTS (
                    SELECT 1 FROM log_entries e
                    WHERE e.log_id = l.id AND e.event_time >= %s
                )
                """
            )
            params.append(parsed_start)

        parsed_end = _parse_filter_time(end_time, "end_time")
        if parsed_end:
            where_clauses.append(
                """
                EXISTS (
                    SELECT 1 FROM log_entries e
                    WHERE e.log_id = l.id AND e.event_time <= %s
                )
                """
            )
            params.append(parsed_end)

        return where_clauses, params

    @staticmethod
    def _row_to_summary(row: dict[str, Any]) -> LogSummary:
        return LogSummary(
            id=row["id"],
            filename=row["original_filename"],
            status=row["status"],
            owner_email=row["owner_email"],
            uploaded_at=_format_datetime(row["uploaded_at"]),
            size_bytes=row["size_bytes"],
            parsed_entries=row["parsed_entries"],
            error_count=row["error_count"],
            warn_count=row["warn_count"],
        )

    @staticmethod
    def _row_to_entry(row: dict[str, Any]) -> LogEntryResponse:
        return LogEntryResponse(
            id=row["id"],
            line_number=row["line_number"],
            timestamp=row["timestamp_text"],
            level=row["level"],
            message=row["message"],
            is_key_event=row["is_key_event"],
        )

    @staticmethod
    def _read_preview(storage_path: str) -> str:
        path = Path(storage_path)

        if not path.exists():
            return ""

        return path.read_text(encoding="utf-8", errors="replace")[:1000]


def parse_log_entries(content: str) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []

    for index, line in enumerate(content.splitlines(), start=1):
        message = line.strip()

        if not message:
            continue

        timestamp_text = _extract_timestamp(message)
        level = _extract_level(message)
        entries.append(
            {
                "line_number": index,
                "event_time": _parse_event_time(timestamp_text),
                "timestamp_text": timestamp_text,
                "level": level,
                "message": message,
                "is_key_event": bool(level in KEY_LEVELS),
            }
        )

    return entries


def _extract_timestamp(line: str) -> str | None:
    match = TIMESTAMP_PATTERN.search(line)
    return match.group("timestamp") if match else None


def _extract_level(line: str) -> str | None:
    match = LEVEL_PATTERN.search(line)

    if not match:
        return None

    return _normalize_level(match.group("level"))


def _normalize_level(level: str) -> str:
    normalized_level = level.upper()
    return "WARN" if normalized_level == "WARNING" else normalized_level


def _parse_event_time(timestamp_text: str | None) -> datetime | None:
    if not timestamp_text or re.match(r"^[A-Z][a-z]{2}\s+", timestamp_text):
        return None

    normalized_timestamp = timestamp_text.replace(" ", "T").replace(",", ".")

    if normalized_timestamp.endswith("Z"):
        normalized_timestamp = f"{normalized_timestamp[:-1]}+00:00"

    try:
        return datetime.fromisoformat(normalized_timestamp)
    except ValueError:
        return None


def _parse_filter_time(value: str | None, field_name: str) -> datetime | None:
    if not value:
        return None

    parsed_time = _parse_event_time(value)

    if parsed_time is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} must be an ISO-like timestamp.",
        )

    return parsed_time


def _format_datetime(value: datetime) -> str:
    return value.isoformat()


log_service = LogService()
