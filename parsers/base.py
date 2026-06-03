from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Dict, Any, Optional
from uuid import UUID


class BaseParser(ABC):
    """Abstract base class for all data source parsers."""

    def __init__(self, source_code: str, source_name: str, api_base_url: str):
        self.source_code = source_code
        self.source_name = source_name
        self.api_base_url = api_base_url
        self.session_headers = {
            "User-Agent": "AI-Radar/1.0 (admin@ai-radar.local)",
            "Accept": "application/json",
        }

    @abstractmethod
    async def fetch(
        self,
        date_from: datetime,
        date_to: datetime,
        filters: Optional[Dict[str, Any]] = None,
        max_items: int = 1000,
        task_id: Optional[UUID] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch raw data from source. Returns list of raw item dicts."""
        pass

    @abstractmethod
    def normalize(self, raw_item: Dict[str, Any]) -> Dict[str, Any]:
        """Convert source-specific format to unified schema."""
        pass

    def get_rate_limit(self) -> Dict[str, int]:
        """Return rate limit config: {requests_per_min, requests_per_hour}."""
        return {"requests_per_min": 30, "requests_per_hour": 500}

    def get_sleep_seconds(self) -> float:
        """Sleep between requests to respect rate limits."""
        rpm = self.get_rate_limit()["requests_per_min"]
        return 60.0 / rpm
