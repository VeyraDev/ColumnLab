from __future__ import annotations

from sqlalchemy.orm import Session

from app.catalog.models.catalog import (
    Column,
    ColumnBlockCatalog,
    Dataset,
    DatasetStatus,
    DatasetVersion,
    ImportJob,
    ImportJobStatus,
    Table,
    VersionStatus,
)


class DatasetRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, *, user_id: int, name: str, source_file_name: str = "") -> Dataset:
        ds = Dataset(user_id=user_id, name=name, source_file_name=source_file_name)
        self.db.add(ds)
        self.db.commit()
        self.db.refresh(ds)
        return ds

    def get(self, dataset_id: int) -> Dataset | None:
        return self.db.get(Dataset, dataset_id)

    def get_for_user(self, dataset_id: int, user_id: int) -> Dataset | None:
        return (
            self.db.query(Dataset)
            .filter(Dataset.id == dataset_id, Dataset.user_id == user_id)
            .first()
        )

    def list_for_user(self, user_id: int, *, ready_only: bool = False) -> list[Dataset]:
        query = self.db.query(Dataset).filter(
            Dataset.user_id == user_id,
            Dataset.status != DatasetStatus.DELETED,
        )
        if ready_only:
            query = query.filter(Dataset.status == DatasetStatus.READY)
        return query.order_by(Dataset.updated_at.desc()).all()

    def update(self, dataset: Dataset) -> Dataset:
        self.db.add(dataset)
        self.db.commit()
        self.db.refresh(dataset)
        return dataset

    def delete(self, dataset: Dataset) -> None:
        dataset.status = DatasetStatus.DELETED
        self.db.add(dataset)
        self.db.commit()


class CatalogRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_version(
        self,
        *,
        dataset_id: int,
        version_no: int,
        storage_path: str,
    ) -> DatasetVersion:
        version = DatasetVersion(
            dataset_id=dataset_id,
            version_no=version_no,
            storage_path=storage_path,
            status=VersionStatus.STAGING,
        )
        self.db.add(version)
        self.db.commit()
        self.db.refresh(version)
        return version

    def get_version(self, version_id: int) -> DatasetVersion | None:
        return self.db.get(DatasetVersion, version_id)

    def get_active_version(self, dataset: Dataset) -> DatasetVersion | None:
        if dataset.active_version_id is None:
            return None
        return self.get_version(dataset.active_version_id)

    def create_table(self, *, version_id: int, name: str, row_count: int, row_group_count: int) -> Table:
        table = Table(
            dataset_version_id=version_id,
            name=name,
            row_count=row_count,
            row_group_count=row_group_count,
        )
        self.db.add(table)
        self.db.commit()
        self.db.refresh(table)
        return table

    def get_table(self, table_id: int) -> Table | None:
        return self.db.get(Table, table_id)

    def list_tables_for_dataset(self, dataset_id: int) -> list[Table]:
        return (
            self.db.query(Table)
            .join(DatasetVersion, Table.dataset_version_id == DatasetVersion.id)
            .filter(DatasetVersion.dataset_id == dataset_id)
            .all()
        )

    def list_tables_for_version(self, version_id: int) -> list[Table]:
        return self.db.query(Table).filter(Table.dataset_version_id == version_id).all()

    def create_column(self, **kwargs) -> Column:
        col = Column(**kwargs)
        self.db.add(col)
        self.db.commit()
        self.db.refresh(col)
        return col

    def list_columns(self, table_id: int) -> list[Column]:
        return (
            self.db.query(Column).filter(Column.table_id == table_id).order_by(Column.ordinal).all()
        )

    def bulk_create_blocks(self, blocks: list[ColumnBlockCatalog]) -> None:
        self.db.add_all(blocks)
        self.db.commit()

    def list_blocks(self, column_id: int) -> list[ColumnBlockCatalog]:
        return (
            self.db.query(ColumnBlockCatalog)
            .filter(ColumnBlockCatalog.column_id == column_id)
            .order_by(ColumnBlockCatalog.block_id)
            .all()
        )

    def finalize_version(
        self,
        version: DatasetVersion,
        *,
        row_count: int,
        table_count: int,
        raw_bytes: int,
        encoded_bytes: int,
    ) -> DatasetVersion:
        version.row_count = row_count
        version.table_count = table_count
        version.raw_bytes = raw_bytes
        version.encoded_bytes = encoded_bytes
        version.status = VersionStatus.READY
        self.db.add(version)
        self.db.commit()
        self.db.refresh(version)
        return version


class ImportJobRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, **kwargs) -> ImportJob:
        job = ImportJob(**kwargs)
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job

    def get(self, job_id: int) -> ImportJob | None:
        return self.db.get(ImportJob, job_id)

    def get_for_user(self, job_id: int, user_id: int) -> ImportJob | None:
        return (
            self.db.query(ImportJob)
            .filter(ImportJob.id == job_id, ImportJob.user_id == user_id)
            .first()
        )

    def update(self, job: ImportJob) -> ImportJob:
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job

    def set_status(self, job: ImportJob, status: str, *, stage: str | None = None) -> ImportJob:
        job.status = status
        if stage is not None:
            job.stage = stage
        return self.update(job)

    def is_cancelled(self, job_id: int) -> bool:
        job = self.get(job_id)
        return job is not None and job.status == ImportJobStatus.CANCELLED
