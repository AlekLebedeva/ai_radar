from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel

class ModelCard(BaseModel):
    id: str
    title: str
    category: Optional[str] = None
    license: Optional[str] = None
    popularity_metric: Optional[int] = None
    summary_ru: Optional[str] = None
    created_at: Optional[datetime] = None
    source_name: Optional[str] = None
    # Новые поля
    model_type: Optional[str] = None
    framework: Optional[str] = None
    task_type: Optional[str] = None
    doi: Optional[str] = None

class ModelDetail(BaseModel):
    raw: Dict[str, Any]
    enriched: Dict[str, Any]

class SourceInfo(BaseModel):
    id: str
    name: str
    code: str
    is_active: bool

class StatsResponse(BaseModel):
    by_category: Dict[str, int]
    by_source: Dict[str, int]