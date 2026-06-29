"""Revision 006 benchmark runs and samples."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "006"
down_revision: str | None = "005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "benchmark_runs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("config_json", sa.Text(), nullable=False),
        sa.Column("env_json", sa.Text(), nullable=True),
        sa.Column("summary_json", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_benchmark_runs_user_id", "benchmark_runs", ["user_id"])

    op.create_table(
        "benchmark_samples",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column("iteration", sa.Integer(), nullable=False),
        sa.Column("phase", sa.String(length=16), nullable=False),
        sa.Column("metric_name", sa.String(length=128), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("extra_json", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["run_id"], ["benchmark_runs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_benchmark_samples_run_id", "benchmark_samples", ["run_id"])


def downgrade() -> None:
    op.drop_index("ix_benchmark_samples_run_id", table_name="benchmark_samples")
    op.drop_table("benchmark_samples")
    op.drop_index("ix_benchmark_runs_user_id", table_name="benchmark_runs")
    op.drop_table("benchmark_runs")
