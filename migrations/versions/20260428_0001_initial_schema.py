"""Create initial Log Assistant schema.

Revision ID: 20260428_0001
Revises:
Create Date: 2026-04-28
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260428_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.UniqueConstraint("email"),
    )

    op.create_table(
        "logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_local_id", sa.Integer(), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("stored_filename", sa.String(length=255), nullable=False),
        sa.Column("storage_path", sa.Text(), nullable=False),
        sa.Column("content_type", sa.String(length=255), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="uploaded"),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.UniqueConstraint("user_id", "user_local_id"),
    )
    op.create_index("idx_logs_user_id", "logs", ["user_id"])
    op.create_index("idx_logs_uploaded_at", "logs", ["uploaded_at"])

    op.create_table(
        "log_entries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("log_id", sa.Integer(), sa.ForeignKey("logs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("line_number", sa.Integer(), nullable=False),
        sa.Column("event_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("timestamp_text", sa.Text(), nullable=True),
        sa.Column("level", sa.String(length=20), nullable=True),
        sa.Column("service_name", sa.String(length=255), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("is_key_event", sa.Boolean(), nullable=False, server_default=sa.text("FALSE")),
    )
    op.create_index("idx_log_entries_log_id", "log_entries", ["log_id"])
    op.create_index("idx_log_entries_level", "log_entries", ["level"])
    op.create_index("idx_log_entries_service_name", "log_entries", ["service_name"])
    op.create_index("idx_log_entries_event_time", "log_entries", ["event_time"])

    op.create_table(
        "analysis_records",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("log_id", sa.Integer(), sa.ForeignKey("logs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("causes", sa.Text(), nullable=False),
        sa.Column("suggestions", sa.Text(), nullable=False),
        sa.Column("analyzed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("idx_analysis_records_log_id", "analysis_records", ["log_id"])


def downgrade() -> None:
    op.drop_index("idx_analysis_records_log_id", table_name="analysis_records")
    op.drop_table("analysis_records")

    op.drop_index("idx_log_entries_event_time", table_name="log_entries")
    op.drop_index("idx_log_entries_service_name", table_name="log_entries")
    op.drop_index("idx_log_entries_level", table_name="log_entries")
    op.drop_index("idx_log_entries_log_id", table_name="log_entries")
    op.drop_table("log_entries")

    op.drop_index("idx_logs_uploaded_at", table_name="logs")
    op.drop_index("idx_logs_user_id", table_name="logs")
    op.drop_table("logs")

    op.drop_table("users")
