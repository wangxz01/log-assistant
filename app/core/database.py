import time

import psycopg
from psycopg.rows import dict_row

from app.core.config import settings


def get_connection() -> psycopg.Connection:
    last_error: psycopg.OperationalError | None = None

    for _ in range(5):
        try:
            return psycopg.connect(settings.database_url, row_factory=dict_row)
        except psycopg.OperationalError as exc:
            last_error = exc
            time.sleep(0.5)

    if last_error:
        raise last_error

    raise RuntimeError("Unable to connect to database.")


def initialize_database() -> None:
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                email VARCHAR(255) NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS logs (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                user_local_id INTEGER NOT NULL,
                original_filename VARCHAR(255) NOT NULL,
                stored_filename VARCHAR(255) NOT NULL,
                storage_path TEXT NOT NULL,
                content_type VARCHAR(255),
                size_bytes INTEGER NOT NULL,
                status VARCHAR(50) NOT NULL DEFAULT 'uploaded',
                uploaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                UNIQUE (user_id, user_local_id)
            );
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS log_entries (
                id SERIAL PRIMARY KEY,
                log_id INTEGER NOT NULL REFERENCES logs(id) ON DELETE CASCADE,
                line_number INTEGER NOT NULL,
                event_time TIMESTAMPTZ,
                timestamp_text TEXT,
                level VARCHAR(20),
                service_name VARCHAR(255),
                message TEXT NOT NULL,
                is_key_event BOOLEAN NOT NULL DEFAULT FALSE
            );
            """
        )
        connection.execute(
            "ALTER TABLE log_entries ADD COLUMN IF NOT EXISTS service_name VARCHAR(255);"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_logs_user_id ON logs(user_id);"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_logs_uploaded_at ON logs(uploaded_at);"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_log_entries_log_id ON log_entries(log_id);"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_log_entries_level ON log_entries(level);"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_log_entries_service_name ON log_entries(service_name);"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_log_entries_event_time ON log_entries(event_time);"
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS analysis_records (
                id SERIAL PRIMARY KEY,
                log_id INTEGER NOT NULL REFERENCES logs(id) ON DELETE CASCADE,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                summary TEXT NOT NULL,
                causes TEXT NOT NULL,
                suggestions TEXT NOT NULL,
                analyzed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            """
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_analysis_records_log_id ON analysis_records(log_id);"
        )
