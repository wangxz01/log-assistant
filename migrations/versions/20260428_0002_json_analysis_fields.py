"""Convert analysis causes/suggestions from TEXT to JSONB

Revision ID: 20260428_0002
Revises: 20260428_0001
"""
from alembic import op

revision = "20260428_0002"
down_revision = "20260428_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE analysis_records
        SET causes = to_jsonb(
            array_remove(ARRAY(SELECT trim(x) FROM unnest(string_to_array(causes, E'\\n\\n')) AS x), ''), 1)
        WHERE causes IS NOT NULL AND causes != ''
        """
    )
    op.execute(
        """
        UPDATE analysis_records
        SET suggestions = to_jsonb(
            array_remove(ARRAY(SELECT trim(x) FROM unnest(string_to_array(suggestions, E'\\n\\n')) AS x), ''), 1)
        WHERE suggestions IS NOT NULL AND suggestions != ''
        """
    )
    op.execute("ALTER TABLE analysis_records ALTER COLUMN causes TYPE JSONB USING causes::jsonb")
    op.execute("ALTER TABLE analysis_records ALTER COLUMN suggestions TYPE JSONB USING suggestions::jsonb")


def downgrade() -> None:
    op.execute("ALTER TABLE analysis_records ALTER COLUMN causes TYPE TEXT USING causes::text")
    op.execute("ALTER TABLE analysis_records ALTER COLUMN suggestions TYPE TEXT USING suggestions::text")
