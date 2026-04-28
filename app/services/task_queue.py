import json
import logging
import threading
import uuid
from typing import Any

import redis

from app.core.config import settings

logger = logging.getLogger(__name__)

TASK_TTL = 86400  # 24 hours


def _get_redis() -> redis.Redis:
    return redis.Redis.from_url(settings.redis_url, decode_responses=True)


def submit_task(log_id: int, user_id: int, user_local_id: int) -> str:
    task_id = uuid.uuid4().hex[:12]
    r = _get_redis()
    r.hset(
        f"task:{task_id}",
        mapping={
            "status": "pending",
            "log_id": str(log_id),
            "user_id": str(user_id),
            "user_local_id": str(user_local_id),
        },
    )
    r.expire(f"task:{task_id}", TASK_TTL)
    r.set(f"task:log:{user_id}:{log_id}", task_id, ex=TASK_TTL)

    thread = threading.Thread(target=_run_task, args=(task_id,), daemon=True)
    thread.start()

    return task_id


def get_task_status(task_id: str) -> dict[str, Any] | None:
    r = _get_redis()
    data = r.hgetall(f"task:{task_id}")
    if not data:
        return None
    return data


def get_task_by_log(log_id: int, user_id: int) -> str | None:
    r = _get_redis()
    return r.get(f"task:log:{user_id}:{log_id}")


def _run_task(task_id: str) -> None:
    r = _get_redis()
    task_key = f"task:{task_id}"

    try:
        r.hset(task_key, "status", "running")

        log_id = int(r.hget(task_key, "log_id"))
        user_id = int(r.hget(task_key, "user_id"))

        from app.core.database import get_connection, initialize_database
        from app.services.ai_service import analyze_log_content

        initialize_database()

        with get_connection() as connection:
            entries = connection.execute(
                "SELECT message FROM log_entries WHERE log_id = %s ORDER BY line_number ASC LIMIT 500",
                (log_id,),
            ).fetchall()

        log_content = "\n".join(e["message"] for e in entries)

        if not log_content.strip():
            r.hset(task_key, mapping={"status": "failed", "error": "No log entries to analyze."})
            return

        result = analyze_log_content(log_content)

        with get_connection() as connection:
            connection.execute(
                "UPDATE logs SET status = %s WHERE id = %s AND user_id = %s",
                ("analyzed", log_id, user_id),
            )
            connection.execute(
                """
                INSERT INTO analysis_records (log_id, user_id, summary, causes, suggestions)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (log_id, user_id, result["summary"], result["causes"], result["suggestions"]),
            )

        r.hset(
            task_key,
            mapping={
                "status": "completed",
                "summary": result["summary"],
                "causes": result["causes"],
                "suggestions": result["suggestions"],
            },
        )

    except Exception:
        logger.exception("Task %s failed", task_id)
        r.hset(task_key, mapping={"status": "failed", "error": "Analysis failed. Please try again."})
