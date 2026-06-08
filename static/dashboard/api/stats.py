from fastapi import APIRouter, Query, Depends
from app.models.schemas import StatsResponse
from app.dependencies import get_data_provider

router = APIRouter(prefix="/api", tags=["stats"])

@router.get("/stats", response_model=StatsResponse)
async def get_stats(
    period: str = Query("all_time", regex="^(week|month|all_time)$"),
    provider = Depends(get_data_provider)
):
    return await provider.get_stats(period)