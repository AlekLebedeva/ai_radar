from typing import List
from fastapi import APIRouter, Depends
from app.models.schemas import SourceInfo
from app.dependencies import get_data_provider

router = APIRouter(prefix="/api", tags=["sources"])

@router.get("/sources", response_model=List[SourceInfo])
async def get_sources(provider = Depends(get_data_provider)):
    return await provider.get_sources()