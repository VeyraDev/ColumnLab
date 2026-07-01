from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse, StreamingResponse
from sqlalchemy.orm import Session

from app.application.benchmark_runner import get_benchmark_runner
from app.application.benchmark_service import BenchmarkService
from app.catalog.schemas.benchmark import BenchmarkSubmitRequest
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.common import success

router = APIRouter(prefix="/api", tags=["benchmarks"])


@router.post("/benchmarks")
def submit_benchmark(
    body: BenchmarkSubmitRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    service = BenchmarkService(db)
    data = service.submit(user_id=user.id, config=body.model_dump())
    return success(data)


@router.get("/benchmarks/{run_id}")
def get_benchmark(
    run_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    service = BenchmarkService(db)
    data = service.get(run_id, user.id)
    if data is None:
        raise HTTPException(status_code=404, detail="benchmark 不存在")
    return success(data)


@router.get("/benchmarks/{run_id}/samples")
def list_benchmark_samples(
    run_id: int,
    offset: int = Query(0, ge=0),
    limit: int = Query(500, ge=1, le=5000),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    service = BenchmarkService(db)
    data = service.list_samples(run_id, user.id, offset=offset, limit=limit)
    if data is None:
        raise HTTPException(status_code=404, detail="benchmark 不存在")
    return success(data)


@router.get("/benchmarks/{run_id}/export.csv")
def export_benchmark_csv(
    run_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    service = BenchmarkService(db)
    csv_text = service.export_csv(run_id, user.id)
    if csv_text is None:
        raise HTTPException(status_code=404, detail="benchmark 不存在")
    return PlainTextResponse(csv_text, media_type="text/csv")


@router.get("/benchmarks/{run_id}/export.json")
def export_benchmark_json(
    run_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    service = BenchmarkService(db)
    json_text = service.export_json(run_id, user.id)
    if json_text is None:
        raise HTTPException(status_code=404, detail="benchmark 不存在")
    return PlainTextResponse(json_text, media_type="application/json")


@router.get("/benchmarks/{run_id}/progress")
def get_benchmark_progress(
    run_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    service = BenchmarkService(db)
    record = service.get(run_id, user.id)
    if record is None:
        raise HTTPException(status_code=404, detail="benchmark 不存在")
    events = get_benchmark_runner().get_events(run_id)
    latest = events[-1] if events else None
    return success(
        {
            "status": record["status"],
            "progress": latest.progress if latest else 0.0,
            "stage": latest.stage if latest else None,
            "message": latest.message if latest else None,
        }
    )


@router.get("/benchmarks/{run_id}/events")
async def benchmark_events(
    run_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    service = BenchmarkService(db)
    record = service.get(run_id, user.id)
    if record is None:
        raise HTTPException(status_code=404, detail="benchmark 不存在")

    runner = get_benchmark_runner()

    async def event_stream():
        cursor = 0
        while True:
            events = runner.get_events(run_id, after=cursor)
            for event in events:
                cursor += 1
                payload = json.dumps(event.to_dict(), ensure_ascii=False)
                yield f"data: {payload}\n\n"
            latest = service.get(run_id, user.id)
            if latest and latest["status"] in ("completed", "failed", "cancelled"):
                if not events:
                    break
                if events and events[-1].stage in ("completed", "failed"):
                    break
            await asyncio.sleep(0.3)

    return StreamingResponse(event_stream(), media_type="text/event-stream")
