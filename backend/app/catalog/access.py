from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.catalog.models.catalog import Column, Dataset, DatasetVersion, Table
from app.catalog.repositories.catalog_repo import CatalogRepository, DatasetRepository


def resolve_table_for_user(db: Session, user_id: int, table_id: int) -> Table:
    catalog = CatalogRepository(db)
    table = catalog.get_table(table_id)
    if table is None:
        raise HTTPException(status_code=404, detail="表不存在")
    _assert_version_access(db, user_id, table.dataset_version_id)
    return table


def resolve_column_for_user(db: Session, user_id: int, column_id: int) -> Column:
    catalog = CatalogRepository(db)
    col = db.get(Column, column_id)
    if col is None:
        raise HTTPException(status_code=404, detail="列不存在")
    table = catalog.get_table(col.table_id)
    if table is None:
        raise HTTPException(status_code=404, detail="表不存在")
    _assert_version_access(db, user_id, table.dataset_version_id)
    return col


def _assert_version_access(db: Session, user_id: int, version_id: int) -> DatasetVersion:
    catalog = CatalogRepository(db)
    datasets = DatasetRepository(db)
    version = catalog.get_version(version_id)
    if version is None:
        raise HTTPException(status_code=404, detail="版本不存在")
    dataset = datasets.get_for_user(version.dataset_id, user_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail="数据集不存在")
    return version
