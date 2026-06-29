"""Revision 002 catalog and import tables."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: str | None = "001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "datasets",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("source_file_name", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("source_sha256", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="draft"),
        sa.Column("active_version_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_datasets_user_id", "datasets", ["user_id"])

    op.create_table(
        "dataset_versions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("dataset_id", sa.Integer(), nullable=False),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column("storage_path", sa.String(length=512), nullable=False),
        sa.Column("format_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("row_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("table_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("raw_bytes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("encoded_bytes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="staging"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["dataset_id"], ["datasets.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_dataset_versions_dataset_id", "dataset_versions", ["dataset_id"])

    op.create_table(
        "import_jobs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("dataset_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("stage", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("source_path", sa.String(length=512), nullable=False),
        sa.Column("staging_path", sa.String(length=512), nullable=False),
        sa.Column("table_name", sa.String(length=200), nullable=False, server_default="data"),
        sa.Column("import_mode", sa.String(length=16), nullable=False, server_default="strict"),
        sa.Column("schema_json", sa.Text(), nullable=True),
        sa.Column("bytes_processed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rows_processed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("current_column", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("error_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_samples_json", sa.Text(), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("target_block_bytes", sa.Integer(), nullable=False, server_default="65536"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["dataset_id"], ["datasets.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_import_jobs_user_id", "import_jobs", ["user_id"])
    op.create_index("ix_import_jobs_dataset_id", "import_jobs", ["dataset_id"])

    op.create_table(
        "tables",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("dataset_version_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("row_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("row_group_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["dataset_version_id"], ["dataset_versions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tables_dataset_version_id", "tables", ["dataset_version_id"])

    op.create_table(
        "columns",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("table_id", sa.Integer(), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("logical_type", sa.String(length=32), nullable=False),
        sa.Column("nullable", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("scale", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("column_file_path", sa.String(length=512), nullable=False),
        sa.Column("block_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("raw_bytes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("encoded_bytes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("min_value_json", sa.Text(), nullable=True),
        sa.Column("max_value_json", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["table_id"], ["tables.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_columns_table_id", "columns", ["table_id"])

    op.create_table(
        "column_block_catalog",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("column_id", sa.Integer(), nullable=False),
        sa.Column("block_id", sa.Integer(), nullable=False),
        sa.Column("row_start", sa.Integer(), nullable=False),
        sa.Column("row_count", sa.Integer(), nullable=False),
        sa.Column("encoding", sa.String(length=16), nullable=False),
        sa.Column("raw_bytes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("encoded_bytes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("null_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("distinct_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("min_repr", sa.String(length=128), nullable=True),
        sa.Column("max_repr", sa.String(length=128), nullable=True),
        sa.Column("run_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("dictionary_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("payload_crc32", sa.String(length=16), nullable=False),
        sa.Column("total_block_length", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["column_id"], ["columns.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_column_block_catalog_column_id", "column_block_catalog", ["column_id"])


def downgrade() -> None:
    op.drop_index("ix_column_block_catalog_column_id", table_name="column_block_catalog")
    op.drop_table("column_block_catalog")
    op.drop_index("ix_columns_table_id", table_name="columns")
    op.drop_table("columns")
    op.drop_index("ix_tables_dataset_version_id", table_name="tables")
    op.drop_table("tables")
    op.drop_index("ix_import_jobs_dataset_id", table_name="import_jobs")
    op.drop_index("ix_import_jobs_user_id", table_name="import_jobs")
    op.drop_table("import_jobs")
    op.drop_index("ix_dataset_versions_dataset_id", table_name="dataset_versions")
    op.drop_table("dataset_versions")
    op.drop_index("ix_datasets_user_id", table_name="datasets")
    op.drop_table("datasets")
