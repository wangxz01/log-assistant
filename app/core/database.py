import time

import psycopg
from psycopg.rows import dict_row

from app.core.config import settings


_migration_checked = False


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
    global _migration_checked

    if _migration_checked:
        return

    expected_revision = _get_head_revision()

    with get_connection() as connection:
        row = connection.execute("SELECT to_regclass('public.alembic_version') AS table_name").fetchone()
        if not row["table_name"]:
            raise RuntimeError("Database migrations have not been applied. Run `alembic upgrade head`.")

        version_row = connection.execute("SELECT version_num FROM alembic_version").fetchone()
        current_revision = version_row["version_num"] if version_row else None

    if current_revision != expected_revision:
        raise RuntimeError(
            "Database schema is not up to date. "
            f"Current revision: {current_revision or 'none'}, expected: {expected_revision}. "
            "Run `alembic upgrade head`."
        )

    _migration_checked = True


def _get_head_revision() -> str:
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    alembic_config = Config("alembic.ini")
    script = ScriptDirectory.from_config(alembic_config)
    return script.get_current_head()
