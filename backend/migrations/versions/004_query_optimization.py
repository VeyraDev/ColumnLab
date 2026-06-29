"""Revision 004 query optimization fields."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "004"
down_revision: str | None = "003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("query_executions", sa.Column("optimized_plan_json", sa.Text(), nullable=True))
    op.add_column("query_executions", sa.Column("optimizer_trace_json", sa.Text(), nullable=True))
    op.add_column("query_executions", sa.Column("block_pruning_json", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("query_executions", "block_pruning_json")
    op.drop_column("query_executions", "optimizer_trace_json")
    op.drop_column("query_executions", "optimized_plan_json")
