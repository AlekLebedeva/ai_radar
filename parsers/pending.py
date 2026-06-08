from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from parsers.base import BaseParser


def _as_utc_naive(value: Any) -> Any:
    if not isinstance(value, datetime):
        return value
    if value.tzinfo is not None:
        return value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


class PendingParserAdapter(BaseParser):
    """Registered parser slot that is not implemented yet."""

    def __init__(
        self,
        source_code: str,
        source_name: str,
        api_base_url: str = "",
        message: Optional[str] = None,
    ):
        super().__init__(source_code, source_name, api_base_url)
        self.message = message or f"Parser '{source_code}' is registered but not implemented yet."

    async def fetch(
        self,
        date_from: datetime,
        date_to: datetime,
        filters: Optional[dict[str, Any]] = None,
        max_items: int = 1000,
        task_id: Optional[UUID] = None,
    ) -> list[dict[str, Any]]:
        raise NotImplementedError(self.message)

    def normalize(self, raw_item: dict[str, Any]) -> dict[str, Any]:
        item = dict(raw_item)
        item["popularity_metric"] = (
            item.get("popularity_metric")
            or item.get("likes")
            or item.get("stars")
            or item.get("downloads")
            or item.get("citations")
        )
        item["created_at_source"] = _as_utc_naive(item.get("created_at_source"))
        item["updated_at_source"] = _as_utc_naive(item.get("updated_at_source"))
        item["domain"] = item.get("domain") or []
        item["tags"] = item.get("tags") or []
        item["language"] = item.get("language") or []
        item["framework"] = item.get("framework") or []
        item["task_type"] = item.get("task_type") or []
        return item
