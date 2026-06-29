"""Revision 003 query execution table."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "003"
down_revision: str | None = "002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "query_executions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("dataset_id", sa.Integer(), nullable=False),
        sa.Column("table_id", sa.Integer(), nullable=False),
        sa.Column("sql_text", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="planned"),
        sa.Column("logical_plan_json", sa.Text(), nullable=True),
        sa.Column("parse_error_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["dataset_id"], ["datasets.id"]),
        sa.ForeignKeyConstraint(["table_id"], ["tables.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_query_executions_user_id", "query_executions", ["user_id"])
    op.create_index("ix_query_executions_dataset_id", "query_executions", ["dataset_id"])
    op.create_index("ix_query_executions_table_id", "query_executions", ["table_id"])


def downgrade() -> None:
    op.drop_index("ix_query_executions_table_id", table_name="query_executions")
    op.drop_index("ix_query_executions_dataset_id", table_name="query_executions")
    op.drop_index("ix_query_executions_user_id", table_name="query_executions")
    op.drop_table("query_executions")
