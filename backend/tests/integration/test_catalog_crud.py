from __future__ import annotations

import pytest

from app.catalog.repositories.catalog_repo import CatalogRepository, DatasetRepository


def test_catalog_crud(db_session, sample_user):
    ds_repo = DatasetRepository(db_session)
    catalog = CatalogRepository(db_session)
    ds = ds_repo.create(user_id=sample_user.id, name="demo", source_file_name="demo.csv")
    version = catalog.create_version(dataset_id=ds.id, version_no=1, storage_path="/tmp/v1")
    table = catalog.create_table(version_id=version.id, name="data", row_count=10, row_group_count=1)
    col = catalog.create_column(
        table_id=table.id,
        ordinal=0,
        name="id",
        logical_type="INT64",
        nullable=1,
        scale=0,
        column_file_path="/tmp/v1/id.col",
        block_count=1,
        raw_bytes=80,
        encoded_bytes=80,
    )
    assert col.name == "id"
    assert catalog.list_columns(table.id)[0].id == col.id
    catalog.finalize_version(version, row_count=10, table_count=1, raw_bytes=80, encoded_bytes=80)
    ds.active_version_id = version.id
    ds_repo.update(ds)
    assert catalog.get_active_version(ds).row_count == 10
