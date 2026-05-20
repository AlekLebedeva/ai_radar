from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from database.session import get_db
from admin.schemas import (
    SourceCreate, SourceOut, TaskCreate, TaskOut, TaskRetry,
    LogOut, LogFilter, StatsOut, PipelineStatus
)
from admin.service import SourceService, TaskService, LogService, StatsService, PipelineService
from parsers.engine import ParserEngine

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


# ─── Sources ───
@router.get("/sources", response_model=List[SourceOut])
async def list_sources(db: AsyncSession = Depends(get_db)):
    svc = SourceService(db)
    return await svc.list()


@router.get("/sources/{code}", response_model=SourceOut)
async def get_source(code: str, db: AsyncSession = Depends(get_db)):
    svc = SourceService(db)
    source = await svc.get(code)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    return source


@router.post("/sources", response_model=SourceOut)
async def create_source(data: SourceCreate, db: AsyncSession = Depends(get_db)):
    svc = SourceService(db)
    return await svc.create(data)


@router.patch("/sources/{code}", response_model=SourceOut)
async def update_source(code: str, data: Dict[str, Any], db: AsyncSession = Depends(get_db)):
    svc = SourceService(db)
    source = await svc.update(code, data)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    return source


@router.post("/sources/{code}/toggle", response_model=SourceOut)
async def toggle_source(code: str, db: AsyncSession = Depends(get_db)):
    svc = SourceService(db)
    source = await svc.toggle(code)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    return source


# ─── Tasks ───
@router.get("/tasks", response_model=List[TaskOut])
async def list_tasks(limit: int = 100, db: AsyncSession = Depends(get_db)):
    svc = TaskService(db)
    return await svc.list(limit)


@router.get("/tasks/{task_id}", response_model=TaskOut)
async def get_task(task_id: UUID, db: AsyncSession = Depends(get_db)):
    svc = TaskService(db)
    task = await svc.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.post("/tasks", response_model=TaskOut)
async def create_task(
    data: TaskCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    svc = TaskService(db)
    task = await svc.create(data, triggered_by="admin")
    # Запускаем парсер в фоне
    engine = ParserEngine(db)
    background_tasks.add_task(engine.run_task, task.id)
    return task


@router.post("/tasks/{task_id}/retry", response_model=TaskOut)
async def retry_task(
    task_id: UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    svc = TaskService(db)
    task = await svc.retry(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    engine = ParserEngine(db)
    background_tasks.add_task(engine.run_task, task.id)
    return task


# ─── Logs ───
@router.get("/logs", response_model=List[LogOut])
async def list_logs(
    parser_name: Optional[str] = None,
    status: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    svc = LogService(db)
    return await svc.list(parser_name, status, date_from, date_to, limit)


# ─── Stats ───
@router.get("/stats", response_model=StatsOut)
async def get_stats(db: AsyncSession = Depends(get_db)):
    svc = StatsService(db)
    return await svc.get()


# ─── Pipeline / DAG ───
@router.get("/pipeline", response_model=PipelineStatus)
async def get_pipeline(db: AsyncSession = Depends(get_db)):
    svc = PipelineService(db)
    return await svc.get_status()
