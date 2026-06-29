"""Revision 005 query execution fields."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "005"
down_revision: str | None = "004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("query_executions", sa.Column("physical_plan_json", sa.Text(), nullable=True))
    op.add_column("query_executions", sa.Column("metrics_json", sa.Text(), nullable=True))
    op.add_column("query_executions", sa.Column("result_json", sa.Text(), nullable=True))
    op.add_column("query_executions", sa.Column("execution_error_json", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("query_executions", "execution_error_json")
    op.drop_column("query_executions", "result_json")
    op.drop_column("query_executions", "metrics_json")
    op.drop_column("query_executions", "physical_plan_json")
