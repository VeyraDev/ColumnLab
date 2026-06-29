from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.application.query_service import QueryService
from app.catalog.schemas.query import QuerySubmitRequest
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.common import success

router = APIRouter(prefix="/api", tags=["queries"])


@router.post("/queries")
def submit_query(
    body: QuerySubmitRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    service = QueryService(db)
    data = service.submit(
        user_id=user.id,
        dataset_id=body.dataset_id,
        sql=body.sql,
        table_id=body.table_id,
    )
    return success(data)


@router.get("/queries/{query_id}")
def get_query(
    query_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    service = QueryService(db)
    return success(service.get_query(user_id=user.id, query_id=query_id))


@router.get("/queries/{query_id}/explain")
def explain_query(
    query_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    service = QueryService(db)
    return success(service.explain(user_id=user.id, query_id=query_id))


@router.get("/queries")
def query_history(
    dataset_id: int = Query(...),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    service = QueryService(db)
    return success(service.history(user_id=user.id, dataset_id=dataset_id, limit=limit))


@router.get("/queries/{query_id}/result")
def query_result(
    query_id: int,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=1000),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    service = QueryService(db)
    return success(service.get_result(user_id=user.id, query_id=query_id, offset=offset, limit=limit))


@router.post("/queries/{query_id}/cancel")
def cancel_query(
    query_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    service = QueryService(db)
    return success(service.cancel(user_id=user.id, query_id=query_id))


@router.get("/queries/{query_id}/events")
async def query_events(
    query_id: int,
    cursor: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    service = QueryService(db)
    record = service.queries.get_for_user(query_id, user.id)
    if record is None:
        raise HTTPException(status_code=404, detail="查询记录不存在")

    async def stream():
        pos = cursor
        while True:
            events = service.get_events(user_id=user.id, query_id=query_id, after=pos)
            for event in events:
                pos += 1
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
            status = service.get_query(user_id=user.id, query_id=query_id)["status"]
            if status in {"completed", "failed", "cancelled"}:
                if not events:
                    yield f"data: {json.dumps({'stage': status, 'message': 'done'})}\n\n"
                break
            await asyncio.sleep(0.3)

    return StreamingResponse(stream(), media_type="text/event-stream")
