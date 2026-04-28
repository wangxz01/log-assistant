#!/usr/bin/env python3
"""Performance benchmark for Log Assistant.

Tests processing time for a 100k-line log file across:
  1. File parsing
  2. Database insert (log metadata + entries)
  3. Entry pagination query
  4. Statistics aggregation query
  5. Log list query
"""

import sys
import time
from pathlib import Path

# Ensure project root is on the path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def measure(label: str, fn) -> float:
    start = time.perf_counter()
    result = fn()
    elapsed = time.perf_counter() - start
    print(f"  {label:<40s} {elapsed:>8.3f}s")
    return elapsed


def main() -> None:
    from tools.log_generator.generate_logs import build_log_lines
    from datetime import datetime, timedelta

    log_path = Path("perf_test_100k.log")

    if not log_path.exists():
        print("Generating 100k-line test log...")
        lines = build_log_lines(start_time=datetime.now() - timedelta(hours=2), count=100000)
        log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        size_mb = log_path.stat().st_size / (1024 * 1024)
        print(f"  Created {log_path} ({size_mb:.1f} MB, {len(lines)} lines)\n")
    else:
        size_mb = log_path.stat().st_size / (1024 * 1024)
        with open(log_path) as f:
            line_count = sum(1 for _ in f)
        print(f"Using existing {log_path} ({size_mb:.1f} MB, {line_count} lines)\n")

    # --- Benchmark 1: Parse log entries ---
    from app.services.log_service import parse_log_entries

    content = log_path.read_text(encoding="utf-8")

    parse_time = measure("1. Parse 100k log entries", lambda: parse_log_entries(content))
    entries = parse_log_entries(content)
    print(f"     -> {len(entries)} entries parsed\n")

    # --- Setup: register a test user ---
    import os
    os.environ.setdefault("POSTGRES_HOST", "localhost")
    os.environ.setdefault("MAX_UPLOAD_SIZE", "52428800")  # 50 MB for test
    os.environ.setdefault("ALLOWED_EXTENSIONS", ".log,.txt")

    from app.core.database import get_connection, initialize_database
    from app.core.security import hash_password

    # Run migrations first
    import subprocess
    subprocess.run(["alembic", "upgrade", "head"], capture_output=True)

    initialize_database()

    test_email = "perf_test@example.com"
    with get_connection() as conn:
        conn.execute("DELETE FROM analysis_records WHERE user_id IN (SELECT id FROM users WHERE email = %s)", (test_email,))
        conn.execute("DELETE FROM log_entries WHERE log_id IN (SELECT id FROM logs WHERE user_id IN (SELECT id FROM users WHERE email = %s))", (test_email,))
        conn.execute("DELETE FROM logs WHERE user_id IN (SELECT id FROM users WHERE email = %s)", (test_email,))
        conn.execute("DELETE FROM users WHERE email = %s", (test_email,))
        conn.execute("INSERT INTO users (email, password_hash) VALUES (%s, %s)", (test_email, hash_password("test1234")))
        user_row = conn.execute("SELECT id FROM users WHERE email = %s", (test_email,)).fetchone()
    user_id = user_row["id"]
    print(f"Test user: {test_email} (id={user_id})\n")

    # --- Benchmark 2: Database insert ---
    def do_insert():
        with get_connection() as conn:
            max_row = conn.execute(
                "SELECT COALESCE(MAX(user_local_id), 0) AS max_id FROM logs WHERE user_id = %s",
                (user_id,),
            ).fetchone()
            user_local_id = max_row["max_id"] + 1

            stored_name = f"perf_test_{user_local_id}.log"
            log_row = conn.execute(
                """INSERT INTO logs (user_id, user_local_id, original_filename, stored_filename, storage_path, content_type, size_bytes, status)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id""",
                (user_id, user_local_id, "perf_test_100k.log", stored_name, str(log_path), "text/plain", log_path.stat().st_size, "parsed"),
            ).fetchone()
            log_id = log_row["id"]

            if entries:
                cur = conn.cursor()
                cur.executemany(
                    """INSERT INTO log_entries (log_id, line_number, event_time, timestamp_text, level, service_name, message, is_key_event)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                    [
                        (log_id, entry["line_number"], entry["event_time"], entry["timestamp_text"],
                         entry["level"], entry["service_name"], entry["message"], entry["is_key_event"])
                        for entry in entries
                    ],
                )
            return log_id

    insert_time = measure("2. Insert 100k entries into PostgreSQL", do_insert)

    with get_connection() as conn:
        log_row = conn.execute(
            "SELECT id, user_local_id FROM logs WHERE user_id = %s ORDER BY id DESC LIMIT 1",
            (user_id,),
        ).fetchone()
    log_id = log_row["id"]
    log_local_id = log_row["user_local_id"]
    print(f"     -> log_id={log_id}, user_local_id=#{log_local_id}\n")

    # --- Benchmark 3: Paginated entry query ---
    def query_page():
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM log_entries WHERE log_id = %s ORDER BY line_number ASC LIMIT 50 OFFSET 49990",
                (log_id,),
            ).fetchall()
        return rows

    page_time = measure("3. Paginated query (page 1000, 50/page)", query_page)
    print(f"     -> {len(query_page())} rows returned\n")

    # --- Benchmark 4: Statistics aggregation ---
    def query_stats():
        with get_connection() as conn:
            levels = conn.execute(
                "SELECT level, COUNT(*) AS count FROM log_entries WHERE log_id = %s GROUP BY level",
                (log_id,),
            ).fetchall()
            services = conn.execute(
                "SELECT COALESCE(service_name,'(none)') AS svc, COUNT(*) AS count FROM log_entries WHERE log_id = %s GROUP BY service_name ORDER BY count DESC LIMIT 10",
                (log_id,),
            ).fetchall()
            trend = conn.execute(
                """SELECT to_char(date_trunc('hour', event_time), 'YYYY-MM-DD"T"HH24:MI:00') AS tb, level, COUNT(*) AS count
                   FROM log_entries WHERE log_id = %s AND event_time IS NOT NULL
                   GROUP BY date_trunc('hour', event_time), level ORDER BY tb""",
                (log_id,),
            ).fetchall()
        return levels, services, trend

    stats_time = measure("4. Statistics aggregation (level/service/trend)", query_stats)
    levels, services, trend = query_stats()
    print(f"     -> {len(levels)} levels, {len(services)} services, {len(trend)} trend points\n")

    # --- Benchmark 5: Log list with keyword filter ---
    def query_list():
        with get_connection() as conn:
            rows = conn.execute(
                """SELECT l.id, l.user_local_id, l.original_filename, l.status, l.uploaded_at, l.size_bytes
                   FROM logs l WHERE l.user_id = %s ORDER BY l.uploaded_at DESC""",
                (user_id,),
            ).fetchall()
        return rows

    list_time = measure("5. Log list query", query_list)
    print()

    # --- Benchmark 6: Keyword filter on entries ---
    def query_keyword():
        with get_connection() as conn:
            total = conn.execute(
                "SELECT COUNT(*) AS cnt FROM log_entries WHERE log_id = %s AND message ILIKE '%%database%%'",
                (log_id,),
            ).fetchone()["cnt"]
        return total

    kw_time = measure("6. Keyword search (ILIKE '%database%')", query_keyword)
    kw_count = query_keyword()
    print(f"     -> {kw_count} matching entries\n")

    # --- Cleanup ---
    with get_connection() as conn:
        conn.execute("DELETE FROM log_entries WHERE log_id = %s", (log_id,))
        conn.execute("DELETE FROM logs WHERE id = %s", (log_id,))
        conn.execute("DELETE FROM users WHERE id = %s", (user_id,))

    # --- Summary ---
    total = parse_time + insert_time + page_time + stats_time + list_time + kw_time
    print("=" * 60)
    print(f"{'TOTAL':40s} {total:>8.3f}s")
    print("=" * 60)


if __name__ == "__main__":
    main()
