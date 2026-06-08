from typing import List, Dict, Any, Tuple
import pandas as pd
from app.models.schemas import ModelCard, ModelDetail, SourceInfo, StatsResponse

class DataProvider:
    """Базовый класс для получения данных из разных источников"""
    async def get_models(self, filters: dict, page: int, limit: int, sort_by: str) -> Tuple[List[ModelCard], int]:
        raise NotImplementedError

    async def get_model_detail(self, model_id: str) -> ModelDetail:
        raise NotImplementedError

    async def get_sources(self) -> List[SourceInfo]:
        raise NotImplementedError

    async def get_stats(self, period: str) -> StatsResponse:
        raise NotImplementedError

    async def get_filtered_dataframe(self, filters: dict) -> pd.DataFrame:
        """Возвращает отфильтрованный DataFrame для экспорта"""
        raise NotImplementedError