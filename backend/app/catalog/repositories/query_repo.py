from __future__ import annotations

from sqlalchemy.orm import Session

from app.catalog.models.catalog import QueryExecution


class QueryRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, **kwargs) -> QueryExecution:
        record = QueryExecution(**kwargs)
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def get(self, query_id: int) -> QueryExecution | None:
        return self.db.get(QueryExecution, query_id)

    def get_for_user(self, query_id: int, user_id: int) -> QueryExecution | None:
        return (
            self.db.query(QueryExecution)
            .filter(QueryExecution.id == query_id, QueryExecution.user_id == user_id)
            .first()
        )

    def list_for_dataset(self, dataset_id: int, *, limit: int = 20) -> list[QueryExecution]:
        return (
            self.db.query(QueryExecution)
            .filter(QueryExecution.dataset_id == dataset_id)
            .order_by(QueryExecution.created_at.desc())
            .limit(limit)
            .all()
        )

    def update(self, record: QueryExecution) -> QueryExecution:
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record
