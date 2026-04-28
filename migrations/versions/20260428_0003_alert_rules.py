"""Add alert rules table

Revision ID: 20260428_0003
Revises: 20260428_0002
"""
from alembic import op

revision = "20260428_0003"
down_revision = "20260428_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS alert_rules (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            name VARCHAR(200) NOT NULL,
            condition_level VARCHAR(50),
            condition_keyword VARCHAR(200),
            condition_service VARCHAR(200),
            threshold INTEGER NOT NULL DEFAULT 1,
            enabled BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMP NOT NULL DEFAULT NOW()
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS alert_rules")
