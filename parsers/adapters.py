import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from parsers.base import BaseParser
from parsers.parse import HuggingFaceModelsParser
from parsers.reddit_parser import RedditParser
from parsers.task import ParserRunTask


def _as_utc_naive(value: Any) -> Any:
    if not isinstance(value, datetime):
        return value
    if value.tzinfo is not None:
        return value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


def _as_utc_aware(value: Any) -> Any:
    if not isinstance(value, datetime):
        return value
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


class HuggingFaceAdapter(BaseParser):
    def __init__(self):
        super().__init__("huggingface", "HuggingFace", "https://huggingface.co/api")
        self._parser: Optional[HuggingFaceModelsParser] = None

    async def fetch(self, date_from, date_to, filters=None, max_items=1000, task_id: Optional[uuid.UUID] = None):
        if self._parser is None:
            self._parser = HuggingFaceModelsParser()

        task = ParserRunTask(
            task_id=task_id or uuid.uuid4(),
            parser_name="huggingface",
            date_from=_as_utc_aware(date_from),
            date_to=_as_utc_aware(date_to),
            source_type="huggingface",
            filters=filters or {},
            max_items=max_items,
            parse_all_categories=bool((filters or {}).get("parse_all_categories", False)),
            delay_seconds=float((filters or {}).get("delay_seconds", 0) or 0),
            delay_between_items=float((filters or {}).get("delay_between_items", 0) or 0),
        )

        return await asyncio.to_thread(self._parser.run, task)

    def normalize(self, raw_item: dict[str, Any]) -> dict[str, Any]:
        item = dict(raw_item)
        item["popularity_metric"] = item.get("popularity_metric") or item.get("likes") or item.get("downloads")
        item["created_at_source"] = _as_utc_naive(item.get("created_at_source"))
        item["updated_at_source"] = _as_utc_naive(item.get("updated_at_source"))
        item["domain"] = item.get("domain") or []
        item["tags"] = item.get("tags") or []
        item["language"] = item.get("language") or []
        item["framework"] = item.get("framework") or []
        item["task_type"] = item.get("task_type") or []
        return item


class RedditAdapter(BaseParser):
    def __init__(self):
        super().__init__("reddit", "Reddit", "https://oauth.reddit.com")
        self._parser: Optional[RedditParser] = None

    async def fetch(self, date_from, date_to, filters=None, max_items=1000, task_id: Optional[uuid.UUID] = None):
        if self._parser is None:
            self._parser = RedditParser()

        task = ParserRunTask(
            task_id=task_id or uuid.uuid4(),
            parser_name="reddit",
            date_from=_as_utc_aware(date_from),
            date_to=_as_utc_aware(date_to),
            source_type="reddit",
            filters=filters or {},
            max_items=max_items,
        )

        return await asyncio.to_thread(self._parser.run, task)

    def normalize(self, raw_item: dict[str, Any]) -> dict[str, Any]:
        item = dict(raw_item)
        item["popularity_metric"] = item.get("popularity_metric") or item.get("likes")
        item["created_at_source"] = _as_utc_naive(item.get("created_at_source"))
        item["updated_at_source"] = _as_utc_naive(item.get("updated_at_source"))
        item["domain"] = item.get("domain") or ["Reddit"]
        item["tags"] = item.get("tags") or []
        item["language"] = item.get("language") or []
        item["framework"] = item.get("framework") or []
        item["task_type"] = item.get("task_type") or []
        return item
