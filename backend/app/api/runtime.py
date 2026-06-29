from __future__ import annotations

import psutil
from fastapi import APIRouter, Depends

from app.catalog.schemas.runtime import RuntimeOut
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.common import success

router = APIRouter(prefix="/api", tags=["runtime"])


@router.get("/runtime")
def get_runtime(_user: User = Depends(get_current_user)) -> dict:
    vm = psutil.virtual_memory()
    proc = psutil.Process()
    payload = RuntimeOut(
        engine_version="0.1",
        memory_used_bytes=int(vm.used),
        memory_total_bytes=int(vm.total),
        process_rss_bytes=int(proc.memory_info().rss),
    )
    return success(payload.model_dump())
