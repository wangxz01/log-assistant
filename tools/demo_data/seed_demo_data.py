from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config import settings
from app.core.database import get_connection, initialize_database
from app.core.security import hash_password
from app.services.log_service import parse_log_entries


DEMO_EMAIL = "demo@example.com"
DEMO_PASSWORD = "demo12345"
DEMO_FILENAME = "demo_checkout_failure.log"


DEMO_LINES = [
    "2026-04-28T10:00:01Z INFO service=checkout request_id=req-1001 cart validation started",
    "2026-04-28T10:00:03Z WARN service=checkout request_id=req-1001 payment provider latency exceeded 1800ms",
    "2026-04-28T10:00:05Z ERROR service=payment request_id=req-1001 timeout while calling bank gateway",
    "2026-04-28T10:00:06Z ERROR service=payment request_id=req-1001 timeout while calling bank gateway",
    "2026-04-28T10:00:08Z WARN service=checkout request_id=req-1002 retrying payment confirmation",
    "2026-04-28T10:00:10Z ERROR service=postgres request_id=req-1002 database connection pool exhausted",
    "2026-04-28T10:00:11Z ERROR service=postgres request_id=req-1002 database connection pool exhausted",
    "2026-04-28T10:00:14Z WARN service=redis request_id=req-1003 cache miss rate above threshold",
    "2026-04-28T10:00:17Z ERROR service=checkout request_id=req-1004 HTTP 502 returned from payment service",
    "2026-04-28T10:00:18Z ERROR service=checkout request_id=req-1004 HTTP 502 returned from payment service",
    "2026-04-28T10:00:20Z INFO service=checkout request_id=req-1005 order queue drained",
    "2026-04-28T10:00:22Z CRITICAL service=payment request_id=req-1006 circuit breaker opened after repeated timeout",
]


def main() -> None:
    initialize_database()
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    storage_path = upload_dir / DEMO_FILENAME
    content = "\n".join(DEMO_LINES) + "\n"
    storage_path.write_text(content, encoding="utf-8")
    entries = parse_log_entries(content)

    with get_connection() as connection:
        connection.execute("DELETE FROM users WHERE email = %s", (DEMO_EMAIL,))
        user_row = connection.execute(
            "INSERT INTO users (email, password_hash) VALUES (%s, %s) RETURNING id",
            (DEMO_EMAIL, hash_password(DEMO_PASSWORD)),
        ).fetchone()
        user_id = user_row["id"]

        log_row = connection.execute(
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
                user_id,
                1,
                DEMO_FILENAME,
                DEMO_FILENAME,
                str(storage_path),
                "text/plain",
                len(content.encode("utf-8")),
                "analyzed",
            ),
        ).fetchone()
        log_id = log_row["id"]

        for entry in entries:
            connection.execute(
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
                (
                    log_id,
                    entry["line_number"],
                    entry["event_time"],
                    entry["timestamp_text"],
                    entry["level"],
                    entry["service_name"],
                    entry["message"],
                    entry["is_key_event"],
                ),
            )

        connection.execute(
            """
            INSERT INTO analysis_records (log_id, user_id, summary, causes, suggestions)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                log_id,
                user_id,
                "结账链路在 10:00:03 后出现连续支付超时，并伴随数据库连接池耗尽。主要影响 checkout、payment 和 postgres 服务。",
                "支付网关调用重复超时，导致 payment 服务触发熔断。\n\nPostgreSQL 连接池耗尽，可能放大了结账请求延迟。\n\nRedis 缓存命中下降，增加了后端数据库压力。",
                "先检查 payment 服务到银行网关的网络和超时配置。\n\n查看 PostgreSQL 连接池上限、慢查询和连接泄漏。\n\n恢复后观察 checkout 服务 HTTP 502 是否下降，并补充支付链路告警。",
            ),
        )

    print(f"Demo user: {DEMO_EMAIL}")
    print(f"Demo password: {DEMO_PASSWORD}")
    print("Demo log id: #1")


if __name__ == "__main__":
    main()
