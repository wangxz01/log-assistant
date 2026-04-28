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
    AlertEvalResponse,
    AlertRule,
    AlertRuleCreate,
    AlertRuleEval,
    AlertRuleListResponse,
    AnalysisHistoryResponse,
    AnalysisRecord,
    AnalyzeResponse,
    AnalyzeStatusResponse,
    BatchLogUploadResponse,
    LogDetailResponse,
    LogEntryResponse,
    LogListResponse,
    LogSummary,
    LogUploadResponse,
    StatsResponse,
)


TIMESTAMP_PATTERN = re.compile(
    r"(?P<timestamp>"
    r"\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:[.,]\d+)?(?:Z|[+-]\d{2}:?\d{2})?"
    r"|[A-Z][a-z]{2}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}"
    r")"
)
LEVEL_PATTERN = re.compile(r"\b(?P<level>TRACE|DEBUG|INFO|WARN|WARNING|ERROR|FATAL|CRITICAL)\b", re.IGNORECASE)
SERVICE_FIELD_PATTERN = re.compile(
    r"\b(?:service|module|component|logger|app)[=:]\s*(?P<service>[\w.-]+)",
    re.IGNORECASE,
)
BRACKET_SERVICE_PATTERN = re.compile(r"\[(?P<service>[a-z][\w.-]{2,})\]", re.IGNORECASE)
KEY_LEVELS = {"WARN", "WARNING", "ERROR", "FATAL", "CRITICAL"}


class LogService:
    async def upload(self, file: UploadFile, user: User) -> LogUploadResponse:
        initialize_database()

        file_bytes = await file.read()
        original_filename = Path(file.filename or "uploaded.log").name

        if not file_bytes:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File is empty.")

        if len(file_bytes) > settings.max_upload_size:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File too large. Maximum size is {settings.max_upload_size // (1024 * 1024)} MB.",
            )

        ext = Path(original_filename).suffix.lower()
        allowed = [e.strip().lower() for e in settings.allowed_extensions.split(",")]
        if ext not in allowed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file type '{ext}'. Allowed: {', '.join(allowed)}",
            )

        decoded = file_bytes.decode("utf-8", errors="replace")
        replacement_count = decoded.count("�")
        if replacement_count > len(decoded) * 0.3:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File contains too many unrecognizable characters. Please upload a valid text file.",
            )
        stored_filename = f"{uuid.uuid4().hex}_{original_filename}"
        upload_dir = Path(settings.upload_dir)
        upload_dir.mkdir(parents=True, exist_ok=True)
        storage_path = upload_dir / stored_filename
        storage_path.write_bytes(file_bytes)

        entries = parse_log_entries(decoded)

        with get_connection() as connection:
            max_row = connection.execute(
                "SELECT COALESCE(MAX(user_local_id), 0) AS max_id FROM logs WHERE user_id = %s",
                (user.id,),
            ).fetchone()
            user_local_id = max_row["max_id"] + 1

            row = connection.execute(
                """
                INSERT INTO logs (
                    user_id,
                    user_local_id,
                    original_filename,
                    stored_filename,
                    storage_path,
                    content_type,
                    size_bytes,
                    status
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    user.id,
                    user_local_id,
                    original_filename,
                    stored_filename,
                    str(storage_path),
                    file.content_type,
                    len(file_bytes),
                    "parsed",
                ),
            ).fetchone()
            log_id = row["id"]

            if entries:
                cursor = connection.cursor()
                cursor.executemany(
                    """
                    INSERT INTO log_entries (
                        log_id,
                        line_number,
                        event_time,
                        timestamp_text,
                        level,
                        service_name,
                        message,
                        is_key_event
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    [
                        (
                            log_id,
                            entry["line_number"],
                            entry["event_time"],
                            entry["timestamp_text"],
                            entry["level"],
                            entry["service_name"],
                            entry["message"],
                            entry["is_key_event"],
                        )
                        for entry in entries
                    ],
                )

        return LogUploadResponse(
            id=user_local_id,
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
        status: str | None = None,
        service: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
        page: int = 1,
        per_page: int = 20,
    ) -> LogListResponse:
        initialize_database()
        where_clauses, params = self._build_log_filters(user, keyword, level, status, service, start_time, end_time)

        with get_connection() as connection:
            total = connection.execute(
                f"SELECT COUNT(*) AS cnt FROM logs l JOIN users u ON u.id = l.user_id WHERE {' AND '.join(where_clauses)}",
                tuple(params),
            ).fetchone()["cnt"]

            offset = (page - 1) * per_page
            rows = connection.execute(
                f"""
                SELECT
                    l.id,
                    l.user_local_id,
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
                LIMIT %s OFFSET %s
                """,
                tuple(params + [per_page, offset]),
            ).fetchall()

        return LogListResponse(
            items=[self._row_to_summary(row) for row in rows],
            total=total,
            page=page,
            per_page=per_page,
            total_pages=max(1, -(-total // per_page)),
        )

    def get_log(
        self,
        user_local_id: int,
        user: User,
        keyword: str | None = None,
        level: str | None = None,
        service: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
        page: int = 1,
        per_page: int = 50,
    ) -> LogDetailResponse:
        initialize_database()
        log = self._get_log_row(user_local_id, user)
        entries, total_entries = self._get_entry_rows(log["id"], keyword, level, service, start_time, end_time, page, per_page)
        total_stats = self._get_log_stats(log["id"])

        return LogDetailResponse(
            id=user_local_id,
            filename=log["original_filename"],
            status=log["status"],
            owner_email=log["owner_email"],
            uploaded_at=_format_datetime(log["uploaded_at"]),
            size_bytes=log["size_bytes"],
            content_preview=self._read_preview(log["storage_path"]),
            entries=[self._row_to_entry(row) for row in entries],
            parsed_entries=len(entries),
            error_count=sum(1 for e in entries if e["is_key_event"] and e["level"] in ("ERROR", "FATAL", "CRITICAL")),
            warn_count=sum(1 for e in entries if e["is_key_event"] and e["level"] == "WARN"),
            total_parsed_entries=total_stats["parsed_entries"],
            total_error_count=total_stats["error_count"],
            total_warn_count=total_stats["warn_count"],
            total_entries=total_entries,
            page=page,
            per_page=per_page,
            total_pages=max(1, -(-total_entries // per_page)),
        )

    def analyze(self, user_local_id: int, user: User) -> AnalyzeResponse:
        initialize_database()
        log = self._get_log_row(user_local_id, user)
        log_id = log["id"]

        from app.services.task_queue import get_task_by_log, submit_task

        existing_task_id = get_task_by_log(log_id, user.id)
        if existing_task_id:
            from app.services.task_queue import get_task_status

            existing = get_task_status(existing_task_id)
            if existing and existing.get("status") in ("pending", "running"):
                return AnalyzeResponse(log_id=user_local_id, task_id=existing_task_id, status=existing["status"])

        task_id = submit_task(log_id, user.id, user_local_id)

        return AnalyzeResponse(
            log_id=user_local_id,
            task_id=task_id,
            status="pending",
        )

    def get_analyze_status(self, user_local_id: int, user: User) -> AnalyzeStatusResponse:
        initialize_database()
        log = self._get_log_row(user_local_id, user)
        log_id = log["id"]

        from app.services.task_queue import get_task_by_log, get_task_status

        task_id = get_task_by_log(log_id, user.id)
        if not task_id:
            return AnalyzeStatusResponse(task_id="", status="none")

        data = get_task_status(task_id)
        if not data:
            return AnalyzeStatusResponse(task_id=task_id, status="none")

        import json as _json

        def _parse_list(value):
            if isinstance(value, list):
                return value
            if isinstance(value, str):
                try:
                    parsed = _json.loads(value)
                    return parsed if isinstance(parsed, list) else [value]
                except (_json.JSONDecodeError, ValueError):
                    return [line.strip() for line in value.split("\n") if line.strip()] or [value]
            return value

        return AnalyzeStatusResponse(
            task_id=task_id,
            status=data.get("status", "none"),
            summary=data.get("summary"),
            causes=_parse_list(data.get("causes")) if data.get("causes") else None,
            suggestions=_parse_list(data.get("suggestions")) if data.get("suggestions") else None,
            error=data.get("error"),
        )

    def list_analyses(self, user_local_id: int, user: User) -> AnalysisHistoryResponse:
        initialize_database()
        log = self._get_log_row(user_local_id, user)
        log_id = log["id"]

        with get_connection() as connection:
            rows = connection.execute(
                """
                SELECT id, summary, causes, suggestions, analyzed_at
                FROM analysis_records
                WHERE log_id = %s AND user_id = %s
                ORDER BY analyzed_at DESC
                """,
                (log_id, user.id),
            ).fetchall()

        return AnalysisHistoryResponse(
            items=[
                AnalysisRecord(
                    id=row["id"],
                    summary=row["summary"],
                    causes=row["causes"],
                    suggestions=row["suggestions"],
                    analyzed_at=_format_datetime(row["analyzed_at"]),
                )
                for row in rows
            ],
        )

    def _get_log_row(self, user_local_id: int, user: User) -> dict[str, Any]:
        with get_connection() as connection:
            row = connection.execute(
                """
                SELECT
                    l.id,
                    l.user_local_id,
                    l.original_filename,
                    l.status,
                    l.uploaded_at,
                    l.size_bytes,
                    l.storage_path,
                    u.email AS owner_email
                FROM logs l
                JOIN users u ON u.id = l.user_id
                WHERE l.user_local_id = %s AND l.user_id = %s
                """,
                (user_local_id, user.id),
            ).fetchone()

        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Log not found.")

        return row

    def _get_entry_rows(
        self,
        log_id: int,
        keyword: str | None = None,
        level: str | None = None,
        service: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
        page: int = 1,
        per_page: int = 50,
    ) -> tuple[list[dict[str, Any]], int]:
        where_clauses = ["log_id = %s"]
        params: list[Any] = [log_id]

        if keyword:
            where_clauses.append("(message ILIKE %s OR service_name ILIKE %s)")
            params.extend([f"%{keyword}%", f"%{keyword}%"])

        if service:
            where_clauses.append("service_name ILIKE %s")
            params.append(f"%{service}%")

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

        offset = (page - 1) * per_page

        with get_connection() as connection:
            total = connection.execute(
                f"SELECT COUNT(*) AS cnt FROM log_entries WHERE {' AND '.join(where_clauses)}",
                tuple(params),
            ).fetchone()["cnt"]

            rows = connection.execute(
                f"""
                SELECT id, line_number, timestamp_text, level, service_name, message, is_key_event
                FROM log_entries
                WHERE {" AND ".join(where_clauses)}
                ORDER BY line_number ASC
                LIMIT %s OFFSET %s
                """,
                tuple(params + [per_page, offset]),
            ).fetchall()

        return rows, total

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
        status: str | None,
        service: str | None,
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
                        WHERE e.log_id = l.id
                        AND (e.message ILIKE %s OR e.service_name ILIKE %s)
                    )
                )
                """
            )
            params.extend([f"%{keyword}%", f"%{keyword}%", f"%{keyword}%"])

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

        if service:
            where_clauses.append(
                """
                EXISTS (
                    SELECT 1 FROM log_entries e
                    WHERE e.log_id = l.id AND e.service_name ILIKE %s
                )
                """
            )
            params.append(f"%{service}%")

        if status:
            where_clauses.append("l.status = %s")
            params.append(status)

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
            id=row["user_local_id"],
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
            service_name=row["service_name"],
            message=row["message"],
            is_key_event=row["is_key_event"],
        )

    @staticmethod
    def _read_preview(storage_path: str) -> str:
        path = Path(storage_path)

        if not path.exists():
            return ""

        return path.read_text(encoding="utf-8", errors="replace")[:1000]

    def get_stats(self, user_local_id: int, user: User) -> StatsResponse:
        initialize_database()
        log = self._get_log_row(user_local_id, user)
        log_id = log["id"]

        with get_connection() as connection:
            level_rows = connection.execute(
                "SELECT level, COUNT(*) AS count FROM log_entries WHERE log_id = %s GROUP BY level ORDER BY count DESC",
                (log_id,),
            ).fetchall()

            trend_rows = connection.execute(
                """
                SELECT to_char(date_trunc('hour', event_time), 'YYYY-MM-DD"T"HH24:MI:00') AS time_bucket,
                       level, COUNT(*) AS count
                FROM log_entries
                WHERE log_id = %s AND event_time IS NOT NULL
                GROUP BY date_trunc('hour', event_time), level
                ORDER BY time_bucket ASC, level ASC
                """,
                (log_id,),
            ).fetchall()

            service_rows = connection.execute(
                """
                SELECT COALESCE(service_name, '(unknown)') AS service, COUNT(*) AS count
                FROM log_entries
                WHERE log_id = %s
                GROUP BY service_name
                ORDER BY count DESC
                LIMIT 10
                """,
                (log_id,),
            ).fetchall()

        return StatsResponse(
            level_distribution=[{"level": r["level"] or "UNKNOWN", "count": r["count"]} for r in level_rows],
            level_trend=[{"time_bucket": r["time_bucket"], "level": r["level"] or "UNKNOWN", "count": r["count"]} for r in trend_rows],
            service_distribution=[{"service": r["service"], "count": r["count"]} for r in service_rows],
        )

    def list_alert_rules(self, user: User) -> AlertRuleListResponse:
        initialize_database()
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT id, name, condition_level, condition_keyword, condition_service, threshold, enabled, created_at FROM alert_rules WHERE user_id = %s ORDER BY created_at DESC",
                (user.id,),
            ).fetchall()
        return AlertRuleListResponse(
            items=[
                AlertRule(
                    id=r["id"], name=r["name"],
                    condition_level=r["condition_level"], condition_keyword=r["condition_keyword"],
                    condition_service=r["condition_service"], threshold=r["threshold"],
                    enabled=r["enabled"], created_at=_format_datetime(r["created_at"]),
                ) for r in rows
            ],
        )

    def create_alert_rule(self, user: User, data: AlertRuleCreate) -> AlertRule:
        initialize_database()
        with get_connection() as conn:
            row = conn.execute(
                """INSERT INTO alert_rules (user_id, name, condition_level, condition_keyword, condition_service, threshold, enabled)
                   VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id, created_at""",
                (user.id, data.name, data.condition_level, data.condition_keyword, data.condition_service, data.threshold, data.enabled),
            ).fetchone()
        return AlertRule(
            id=row["id"], name=data.name,
            condition_level=data.condition_level, condition_keyword=data.condition_keyword,
            condition_service=data.condition_service, threshold=data.threshold,
            enabled=data.enabled, created_at=_format_datetime(row["created_at"]),
        )

    def delete_alert_rule(self, rule_id: int, user: User) -> None:
        initialize_database()
        with get_connection() as conn:
            result = conn.execute("DELETE FROM alert_rules WHERE id = %s AND user_id = %s", (rule_id, user.id))
            if result.rowcount == 0:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found.")

    def evaluate_alert_rules(self, user_local_id: int, user: User) -> AlertEvalResponse:
        initialize_database()
        log = self._get_log_row(user_local_id, user)
        log_id = log["id"]

        with get_connection() as conn:
            rules = conn.execute(
                "SELECT id, name, condition_level, condition_keyword, condition_service, threshold FROM alert_rules WHERE user_id = %s AND enabled = TRUE",
                (user.id,),
            ).fetchall()

        if not rules:
            return AlertEvalResponse(alerts=[])

        where_parts = [f"log_id = {log_id}"]
        params: list[Any] = []
        entries = self._get_entry_rows(log_id, page=1, per_page=10000)[0]

        alerts = []
        for rule in rules:
            matched = 0
            for entry in entries:
                if rule["condition_level"] and (entry["level"] or "").upper() != (rule["condition_level"] or "").upper():
                    continue
                if rule["condition_keyword"] and rule["condition_keyword"].lower() not in (entry["message"] or "").lower():
                    continue
                if rule["condition_service"] and rule["condition_service"].lower() not in (entry["service_name"] or "").lower():
                    continue
                matched += 1

            triggered = matched >= rule["threshold"]
            alerts.append(AlertRuleEval(
                rule_id=rule["id"], rule_name=rule["name"], triggered=triggered,
                message=f"「{rule['name']}」匹配 {matched} 条，阈值 {rule['threshold']}{' — 已触发' if triggered else ''}",
            ))

        return AlertEvalResponse(alerts=alerts)


def parse_log_entries(content: str) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []

    for index, line in enumerate(content.splitlines(), start=1):
        message = line.strip()

        if not message:
            continue

        timestamp_text = _extract_timestamp(message)
        level = _extract_level(message)
        service_name = _extract_service_name(message)
        entries.append(
            {
                "line_number": index,
                "event_time": _parse_event_time(timestamp_text),
                "timestamp_text": timestamp_text,
                "level": level,
                "service_name": service_name,
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


def _extract_service_name(line: str) -> str | None:
    match = SERVICE_FIELD_PATTERN.search(line)
    if match:
        return match.group("service")

    bracket_match = BRACKET_SERVICE_PATTERN.search(line)
    return bracket_match.group("service") if bracket_match else None


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
